# Hospital Ward Dynamic Contact Network Dataset

## Link:
https://sociopatterns.org/datasets/hospital-ward-dynamic-contact-network/

## Description:
"This dataset contains the temporal network of contacts between patients, patients and health-care workers (HCWs) and among HCWs in a hospital ward in Lyon, France, from Monday, December 6, 2010 at 1:00 pm to Friday, December 10, 2010 at 2:00 pm. The study included 46 HCWs and 29 patients.

The file contains a tab-separated list representing the active contacts during 20-second intervals of the data collection. Each line has the form “t i j Si Sj“, where i and j are the anonymous IDs of the persons in contact, Si and Sj are their statuses (NUR=paramedical staff, i.e. nurses and nurses’ aides; PAT=Patient; MED=Medical doctor; ADM=administrative staff), and the interval during which this contact was active is [ t - 20s, t ]. If multiple contacts are active in a given interval, you will see multiple lines starting with the same value of t. Time is measured in seconds."

## License:
["Estimating Potential Infection Transmission Routes in Hospital Wards Using Wearable Proximity Sensors", PLoS ONE 8(9), e73970 (2013)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0073970)

---

## Spike 3 – Data check (`spikes/inspect_data.py`) — 2026-11-14

```
Total rows:        32,424
Unique people:     75
People per role:
  PAT: 29
  NUR: 27
  MED: 11
  ADM: 8
First timestamp:   140 s
Last timestamp:    347,640 s
Span:              96.53 h (~4 days)
Distinct pairs:    1,139
Contact episodes:  14,037
Busiest person:    id=1115 (NUR), 1,667 episodes
```

**Notes:**
- File is tab-separated with no header; columns are `time_s id_a id_b role_a role_b`. The timestamp is the *end* of the 20 s interval per the dataset description.
- 75 people total: 29 PAT, 27 NUR, 11 MED, 8 ADM. Matches the paper's "46 HCWs and 29 patients."
- Span is ~96.5 h (Mon Dec 6 13:00 to Fri Dec 10 14:00). Aligns with the stated collection window.
- 14,037 episodes after merging consecutive 20 s readings with gap ≤ 20 s. This is the edge count the browser query engine will face.
- Busiest person (1115, nurse) has 1,667 episodes — the high-degree node to watch for query performance in Spike 7.
- **Spike 3 status: PASS.** Data matches the paper, license is CC BY-NC-SA 3.0 (non-commercial hackathon with attribution is fine).

---

## Spike 4 – Relate `docs/limitations.md` review — 2026-11-14

Source: `https://raw.githubusercontent.com/relatedb/relate/main/docs/limitations.md` (v1.0.2) plus skill references `operations.md` and `agent-safety.md`.

### Variable-length paths (`*1..N`)

- Walked **recursively on the native stack**. A bound above the limit is rejected at admission with `TraversalDepthExceeded` before the statement plans or runs.
- Default limit: **500 hops** (knob: `--max-traversal-depth N` / `RELATE_MAX_TRAVERSAL_DEPTH`; max 2000).
- Above 2000 risks a stack-overflow abort with no error or recovery. WASM has the tightest stack (16 MiB); measured abort is ~2,700 hops on debug WASM.
- Unbounded `*` / `*1..` stops at **32 hops** by the classic walk — not covered by the traversal-depth limit.
- `shortestPath(...)` is exempt from the limit and is bounded only by relationship count.
- **Impact for Outbreak Replay:** Our Q1/Q2 expansion is iterative (one hop per round), not a single `*1..N` pattern, so we won't hit this. If we ever write a chain query with an explicit bound (e.g. `[:INFECTED*1..5]`), we're well inside 500. No action needed.

### `reduce`

- A `reduce` accumulator that **wraps itself in a new list each iteration** fails with `ValueDepthExceeded` at **500 container nesting levels**.
- Normal numeric accumulators (summing durations, tracking earliest arrival time) are flat values and are unaffected.
- **Impact:** Our expansion helper accumulates a scalar arrival time — zero risk. No action needed.

### `UNWIND`

- A **materialized `UNWIND`** (the whole list buffered at once) is covered by the per-allocation **expression memory limit** (default 256 MiB). A 1M-row `UNWIND` measures ~48 MB, so the limit is generous.
- Our Q1/Q2 queries `UNWIND $frontier AS f` over a list of at most 75 people — nowhere near the limit.
- Per-statement execution is also bounded by a **100,000-pass budget** (applies to nested `CALL`/`EXISTS`/`FOREACH` evaluations too).
- **Impact:** No risk at ward scale. If we batch-import 32,424 rows in one `UNWIND`, that's ~1.6 MB — fine.

### List functions / comprehensions

- Output of a comprehension is covered by the same **256 MiB per-allocation expression cap**.
- Runtime values (lists, maps) are capped at **500 container nesting levels** (`ValueDepthExceeded`).
- Both limits are fixed — no knob to change the nesting cap; the expression cap has `--expression-memory-limit` / `RELATE_EXPRESSION_MEMORY_LIMIT` (set `0`/`none` to disable for bulk pipelines).
- **Impact:** We collect small lists (`nodes(p)`, `relationships(p)` for a chain of ≤75 people). No risk.

### Indexes

- Standard property, vector, and fulltext indexes are all supported (`CREATE INDEX`, `CREATE VECTOR INDEX`, `CREATE FULLTEXT INDEX`).
- No limitations flagged in `limitations.md` for index creation or use at this scale.
- **Impact:** We can index `Person.id` and `CONTACT.start`/`end` normally. Confirm with `SHOW INDEXES` after import.

### Aggregations (`min`, `max`, `sum`)

- No specific limitations on `min`, `max`, or `sum` in `limitations.md`.
- They are reducing aggregates and count as such for Safe Mode's `LIMIT`-or-aggregate rule (so a `RETURN min(r.start)` without `LIMIT` is accepted in safe mode).
- Subject to the general 100,000-pass per-statement budget and the 256 MiB expression cap, neither of which is a concern at ward scale.
- **Impact:** Q1 uses `min(...)` and `sum(...)`, Q2 uses `max(...)` — all fine.

### File locking

- **One writer process per database at a time.** This applies to both directory and `.rl` bundle forms.
- A second process opening the same file as a writer is **unsupported and not retryable** (exit code 5, `Error::Conflict`).
- For `.rl` bundles specifically: `relate clone` (backup) on a writer-held bundle **fails locked**. Must checkpoint + copy when the writer is idle, or stop the writer first.
- `--read-only` on a `.rl` file is **only allowed while no writer holds it** — unlike directory form, which allows a read-only open beside a writer.
- `--read-only=live` (follow WAL commits) is **directory-only**; refused for `.rl` and `:memory:`.
- Concurrent threads within one process can read together (bounded by 256 in-flight statement slots).
- **Impact for Outbreak Replay:** The Python build script writes `data/ward.relate`; the browser/CLI reads it after the script exits. No concurrent access at build time — no issue. During development, don't run the importer while the CLI is open on the same file.

### Overall Spike 4 verdict

**PASS — no blockers found.** The key constraints to keep in mind:

| Concern | Safe? | Note |
|---|---|---|
| Iterative 1-hop expansion (Q1, Q2) | Yes | Not a variable-length pattern; traversal limit doesn't apply |
| `reduce` for scalar accumulation | Yes | Flat value, never hits 500-level nesting cap |
| `UNWIND $frontier` over ≤75 nodes | Yes | Far below 256 MiB expression cap |
| `min`/`max`/`sum` aggregations | Yes | No limitations at this scale |
| `.rl` file locking | Watch | Python writer must finish before CLI/browser opens the file; `--read-only` on `.rl` requires no active writer |
| Explicit hop bound in chain queries | Watch | Keep `*` bounds ≤ 500 (default); WASM stack tightest surface |

---

## Spike 7 – Import the real ward (`spikes/import_ward.py`) — 2026-11-16

```
Episodes imported:  14,037
People imported:    75
Import time:        0.3 s
File:               data/ward.rl  (3.0 MB, single-file .rl bundle)
Person nodes:       75  ✓
CONTACT rels:       14,037  ✓
```

**Notes:**
- Database written as `data/ward.rl` (`.rl` extension = single-file bundle, required for browser portability).
- Batch size 500 rows per `UNWIND ... CREATE`. Each episode has `start`, `end`, `duration_s`, `day` properties.
- Index created on `Person.id`.
- **Spike 7a (import) status: PASS.**

---

## Spike 7 – Query speed (`spikes/time_queries.py`) — 2026-11-16

Start time: beginning of day 2 (t = 86400 s). No window end limit.

| Seed | id | Reached | Rounds | ms |
|---|---|---|---|---|
| busiest NUR | 1115 | 68 | 5 | 110 |
| typical NUR | 1100 | 64 | 6 | 90 |
| typical PAT | 1305 | 0 | 1 | 0 |

Single expansion round (busiest person, avg 5 runs): **3.3 ms**

**Slowest full investigation: 110 ms — PASS (< 1000 ms target)**

**Notes:**
- PAT 1305 reached 0 people: patient started on day 2 with no contacts in that window — legitimate.
- NUR 1100 takes 6 rounds because the contact network is sparse mid-dataset.
- No fallback (`MET` summary relationship) needed.
- **Spike 7b (query speed) status: PASS.**

---

## Spike 8 – License files — 2026-11-16

- `LICENSE`: MIT, covering all source code.
- `DATA_LICENSE`: CC BY-NC-SA 3.0 for `data/raw/` and `data/ward.rl` (derivative of SocioPatterns dataset, Vanhems et al. 2013). Non-commercial hackathon with attribution is permitted under this license.
- **Spike 8 status: PASS.**

---

## Spike 5 – Rules check — 2026-11-16

Source: https://relate.devpost.com/rules (updated Nov 13, 2026).

**Key findings:**

1. **Persistent store:** The rules have no "persistent store" requirement. The only requirement is "meaningful use of Relate" through CLI, embedded, WASM, MCP, Bolt, HTTP, hybrid retrieval, or Neo4j/Aura connection. A committed `ward.rl` file that judges open via CLI and Python clearly satisfies this. No question needed.

2. **AI-assisted code:** Explicitly allowed (Section 3): *"You may use AI coding tools and models. You remain responsible for the result, including its originality and license compliance, and must describe any significant AI use in your submission."* Must disclose in the submission form.

3. **Third-party data:** Allowed (Section 3): *"Third-party libraries, datasets, models, and assets are allowed if you have the right to use them and comply with their licenses."* CC BY-NC-SA 3.0 fits a non-commercial contest with attribution.

4. **⚠️ Judging criteria differ from the proposal.** The rules list **5 criteria, weighted equally** — not the 30/25/20/15/10 breakdown in docs/plan.md:
   - Creativity
   - Usefulness
   - Completeness (works end to end, runs from setup instructions)
   - Clarity (written explanation, demo, visuals)
   - Effective use of connected context (graph, retrieval, agent features)

   Update the proposal's scorecard to reflect equal weights. "Completeness" is effectively the same as the plan's "Functionality and completeness." "Clarity" maps to "Documentation and reproducibility."

5. **Deadline is Dec 11 at 6 PM PST** — one day later than the Dec 10 date in the plan. Minor, but good to have confirmed.

6. **GitHub topic `relate` is required** (not just recommended) and must remain through winner announcement. `relate-neo4j-hackathon` is recommended. Both already added in Step 0. ✓

7. **New projects only:** Must be started on or after Nov 11, 2026. ✓

**Action items from rules:**
- Update `docs/plan.md` scorecard to equal-weight criteria.
- Submission form must describe significant AI use (Claude Code).
- Keep `relate` topic on the repo through Dec 17.

**Spike 5 status: PASS — no blockers.**

---

## Spike 6 – Duplicate check — 2026-11-16

Sources checked by user: Devpost project gallery, github.com/jexp/relate-ideas issues, GitHub topic search.

- **Devpost gallery:** One match for "hospital" — project "alwarid graph." Not a contact-tracing or epidemic project; not a conflict.
- **relate-ideas issues:** Page not found; no relevant issues.
- **GitHub topic search:** Nothing relevant.

**No near-identical entries found.** Our combination of time-respecting paths, real sensor data, and the investigation/game framing is not duplicated by any entry found.

**Spike 6 status: PASS.**

---

## Spike 1 – File in the browser (`spikes/web/`) — 2026-11-17

App: Vite 5 + TypeScript, `@relate/relate-wasm` 1.0.2, Web Worker.

**Step A — RETURN 1 (hello world)**
```
result: [{"ok":1}]
✓ PASS — WASM loads and runs Cypher in a worker
```

**Step B — load ward data**
- Route 1 (fetch `ward.rl` → OPFS → `RelateDb.open`): **FAIL**
  - Error: `OPFS name must be 1-64 characters from [A-Za-z0-9_-]`
  - Cause: `ward.rl` contains a dot, which is not in the allowed OPFS name charset.
  - Fix available: use `ward-rl` as the OPFS key (rename the handle, not the file). Not pursued — Route 2 is sufficient.
- Route 2 (fetch `ward.json` → in-memory `RelateDb` via batched `UNWIND ... CREATE`): **PASS**
  - Person count: 75 ✓
  - CONTACT rels: 14,037 ✓

**Step C — full investigation in WASM**
```
Seed: person 1115 (NUR), t = 86400 s (start of day 2)
Reached:   68 people  ✓ matches Python
Rounds:    5
WASM time: 639 ms     ✓ PASS (< 1000 ms target)
Wall time: 639 ms
```

WASM is ~6× slower than native Python (110 ms), but well inside the 1-second target.

**Notes:**
- Route 1 is fixable (use a dot-free OPFS key) but Route 2 is simpler and confirmed working.
  For the app, `ward.rl` stays the inspectable store for CLI/Python; the browser loads from `ward.json`.
- Load time for `ward.json` (1.1 MB, 14,037 contacts) via batched UNWIND is not separately timed here — will measure in Spike 11 if needed.
- WASM binary is 7 MB; `ward.json` export is 1.1 MB. Total page weight is acceptable for GitHub Pages.

**Spike 1 status: PASS (Route 2). Go decision: GO.**
