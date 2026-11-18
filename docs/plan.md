# Outbreak Replay: Relate Hackathon Proposal

Nov 14, 2026 · @Thillainayaki

## TL;DR

Build **Outbreak Replay**: a ward exposure investigator for hospital infection-prevention teams. Mark a patient or staff member positive, and it returns who was exposed (with time and duration), the likely source, and the time-ordered chain, all from a contact log stored in one Relate file.

**Revised after a review against the rules (v2).** v1 led with an outbreak *simulator*, which made the user vague ("students and outbreak teams") and the core use case a visualization. v2 leads with the investigation workflow that a real team does today. Simulation stays, but only as the evidence that the tracing works: a policy comparison on the same data.

The Immuni story is now the creative frame, not the product. Immuni kept no graph by design, so it could never show chains. Hospital badge systems already log contacts, and vendors sell reports of direct and secondary exposure. Outbreak Replay adds what those lists miss: time-ordered chains, backward source finding, and an outbreak you can hand over as a file.

Recommendation: go, if spikes 1, 2 and 7 in "Validate before starting" pass by Nov 18. Budget about 60 hours, Nov 15 to Dec 11.

## Requirements and scorecard

v1 would likely have scored in the low 60s out of 100; v2 targets the mid 80s by fixing the user, the query design, and the judge's first five minutes. Scores are my rough estimates against the published criteria ([Devpost](https://relate.devpost.com/)).

**Note (Spike 5, Nov 16):** The actual rules list 5 criteria, all weighted equally (20 pts each). Names and weights below are updated from the confirmed rules. The v1/v2 estimates are kept for relative comparison only.

| Criterion (from rules) | Pts | v1 est. | Main gap in v1 | Fix in v2 | v2 target |
| --- | --- | --- | --- | --- | --- |
| Effective use of connected context | 20 | 13 | Variable-length paths over thousands of repeated contacts could explode or time out. No defined way for judges to explore, which this criterion explicitly scores. | Earliest-arrival expansion queries (see Graph model). Named query file runnable from the CLI. Cypher shown for every answer in the UI. MCP for debrief. | 17 |
| Completeness | 20 | 12 | Core use case was a visualization with many moving parts; no end-to-end path. | Core = three answers for one positive case (exposed, source, chain). Each has a test with a known answer. CI runs named queries. Three ways to run. | 17 |
| Usefulness | 20 | 10 | No clear user or decision. | Infection-prevention team on a ward with badge data, deciding whom to test and isolate. The demo ends on that list. | 16 |
| Clarity | 20 | 13 | README promised but not shaped; demo not planned. | README follows the template exactly. 2-minute narrated video. Show Cypher on every panel. | 16 |
| Creativity | 20 | 14 | Fine. | Immuni frame, time-travel deduction game, AI rival on the same evidence, measured policy comparison on real data. | 17 |
| **Total** | 100 | **62** |  |  | **83** |

**Submission checklist** (do the first two on day one, not at the end):

- [ ] Public GitHub repo created with topics `relate` (required) and `relate-neo4j-hackathon`; confirm it shows at github.com/topics/relate.
- [ ] `data/ward.rl` committed: single-file store judges can open. Raw source data and a `make rebuild` that regenerates it with fixed seeds.
- [ ] Working code with Relate running: CI runs the test suite and every named query in `queries/` against the committed file on each push.
- [ ] README in the template's exact sections (draft below).
- [ ] Devpost description: the use case, and what connects to what (`Person` to `Person` via timed `CONTACT`, cases and runs on top).
- [ ] Demo video, 1 to 2 minutes, screen share is fine.
- [ ] Hosted demo link (GitHub Pages) in both the README and Devpost.

**README draft** (the template asks one question: how are you using Relate, and why):

```markdown
# Outbreak Replay
Find who was exposed, the likely source, and the chain of a hospital ward outbreak, from one Relate file.

## Use case
When a patient or staff member tests positive, infection-prevention teams must decide fast whom to test and isolate. Badge systems log who was near whom, but a flat contact list misses order in time and second-hand exposure. The relationships that matter: person-to-person contacts with start and end times, and the transmission chains they allow.

## How it uses Relate
- Mode: single file (data/ward.relate)
- Why this mode: the whole outbreak travels as one artifact that a judge, an analyst or an agent can open with the CLI, Python or the browser, with nothing to deploy. A directory would split it; memory would lose it.
- What the graph models: Person nodes (role), timed CONTACT relationships merged from 20-second sensor readings, simulation Runs with INFECTED, DETECTED and QUARANTINED edges for policy comparison.

## Setup and run
Try it: https://<user>.github.io/outbreak-replay
Local: `make demo` (installs relate-db, builds nothing, serves the app on localhost)
CLI only: `relate query --database data/ward.relate -f queries/exposed.cypher`

## Where the data lives
data/ward.relate. Raw contacts in data/raw/ (SocioPatterns, CC BY-NC-SA 3.0, attribution in DATA_LICENSE).
```

CLI flags above are placeholders until spike 4 confirms them.

Relate itself launched at NODES on Nov 11, 2026, so it is days old. Expect rough edges in the WebAssembly build and docs, which is why validation comes first ([Neo4j press release](https://neo4j.com/?p=435950)).

## Prior art

Contact tracing on graphs is well trodden, but nothing combines real sensor data, time-respecting chains, a policy comparison, and a portable on-device graph. That combination is the gap.

| Project | What it does | What it lacks that we add |
| --- | --- | --- |
| [Immuni](https://developers.italia.it/en/software/github.com/immuni-app/immuni) (Bending Spoons, 2020 to 2022) | Italy's exposure app on the Apple/Google framework. Matching ran on the phone, and it used only exposure duration and Bluetooth attenuation to score risk. | By design it kept no graph, so it could never see chains, sources, or second-order exposure. This is our story hook. |
| [Neo4j contact-tracing example](https://github.com/neo4j-graph-examples/contact-tracing) (Rik van Bruggen) | Synthetic people, places, and visits in a Neo4j sandbox, with GDS algorithms. | Server-bound, synthetic data, no time-respecting paths, no policy comparison. Judges know it, so we must clearly go past it. |
| [COCOM Brussels](https://neo4j.com/customer-stories/cocom/) and [Geneva](https://neo4j.com/?p=143952) deployments | Real health-agency tracing on Neo4j. Brussels found 5,000+ clusters. Geneva used transmission dates to support backward tracing. | Enterprise, central server, private data. We cite them as proof the use case is real. |
| [EoN (Epidemics on Networks)](https://epidemicsonnetworks.readthedocs.io/) | Python package for SIR/SIS simulation on NetworkX graphs, can return who infected whom. | A simulator, not a store or a query surface. We may borrow its model, not compete with it. |
| [What Happens Next?](https://ncase.me/covid-19/) (Nicky Case and Marcel Salathé) | The best-known playable epidemic explainer. | Compartment curves, no network, no real data. Sets the bar for polish and storytelling. |
| [Endo et al., backward tracing](https://doaj.org/article/1d536a71aed0438f886d5e878dd980ef) | Branching-process model showing backward tracing finds sources with 3 to 10 times more infections than average, and cuts later cases by 2 to 3 times. | A paper, not a tool. We turn its claim into something you can run on real contact data. |
| Hospital RTLS badge systems (Midmark, CenTrak, RFiD Discovery) | Staff and patients wear badges; a report lists who had direct and secondary exposure to a contagious person, in minutes instead of days of interviews. Wake Forest stood one up in a week for Ebola in 2014. | Proprietary, server-bound flat lists. No time-ordered chains, no backward source ranking, no portable outbreak file. This is our real user, and the bar we must beat. |

The dataset is the [SocioPatterns Lyon hospital ward network](https://pmc.ncbi.nlm.nih.gov/articles/PMC3770639): face-to-face contacts between patients and staff in a geriatric unit, logged in 20-second intervals across about four days in December 2010. Roles (doctor, nurse, admin, patient) are included. Its license is CC BY-NC-SA, which fits a non-commercial hackathon with attribution ([Netzschleuder](https://networks.skewed.de/net/sp_hospital)). Other SocioPatterns sets (schools, conferences) give a second scenario if time allows.

## How to stand out

Most entries will be agent-memory or chat-over-docs projects. We win on four things those can't show: time as a first-class graph dimension, real data, a measurable result, and a story judges remember.

1. **Time-respecting paths, not just paths.** A naive k-hop query says A met B and B met C, so A could infect C. That is wrong if B met C *before* meeting A. Every chain query filters edges so contact times increase along the path. This is the one idea that makes the graph necessary, and most contact-tracing demos skip it. (30 pts: Relate and connected context)
2. **A measured policy shootout.** Run the same seeded outbreak under three policies: none, one-hop forward (Immuni-style), and graph backward plus forward tracing. Report infections averted and people quarantined per infection averted. Then check whether Endo et al.'s 2 to 3 times effect shows up on real ward contacts. A number on screen beats a pretty graph. (20 pts: Usefulness, 10 pts: Creativity)
3. **The outbreak is a file.** One `.relate` file per scenario holds contacts, the simulated infections, and every policy run. Anyone can open it in the CLI, Python, or the browser and re-ask questions. This fits Relate's "one file carries the whole graph" pitch exactly, and it is the inspectable store the rules ask for. (15 pts: Docs and reproducibility)
4. **Ask the outbreak.** A small MCP or natural-language panel: "Who is the most likely source of the cluster on day 3?" turns into Cypher shown on screen, then runs locally. It shows the agent angle Neo4j is pushing without becoming the whole project.
5. **The Immuni framing.** Bending Spoons built Immuni, and it deliberately kept no graph to protect privacy. Our pitch: keep the graph, but only on the device. That is a creative, on-theme answer to "why embedded?", and it ties to the portfolio doc in the ideas repo.

What we will *not* do: a generic COVID dashboard, a map of cases, or a custom simulator with dozens of knobs. Those look like 2020 hackathon projects.

## Product concept and demo

The app opens on an investigation, not a simulation: one page with the ward graph, a time scrubber, and a case panel that answers the three questions an infection-prevention nurse asks after a positive test.

**Core flow (the MVP, must work end to end)**

1. **Open the ward.** `ward.relate` loads in the browser; people are grouped by role, and only contacts inside the scrubber window are drawn.
2. **Report a case.** Pick a person, the positive-test time, and the infectious window (default: 48 hours before, editable).
3. **Who was exposed?** A ranked list: direct and second-hand, earliest exposure time, cumulative contact minutes, and a threshold filter (for example 15 minutes). Export as CSV, the "test and isolate" list.
4. **Where did it come from?** With two or more cases reported, rank likely sources by how many cases each could have reached in time.
5. **How did it get there?** Click anyone to see the time-ordered chain, with contact times on each edge.
6. **Show Cypher** on every panel: the exact query, copyable, runnable from the CLI against the same file.

**Evidence tab (still MVP, precomputed)**: the same outbreak replayed 50 times under three policies (none, direct contacts only, chains plus backward source). The card shows cases prevented and people isolated per case prevented. This is what proves the tool is useful, rather than claiming it.

**2-minute video script**

| Time | On screen | Voiceover point |
| --- | --- | --- |
| 0:00 to 0:12 | Immuni "you were exposed" screen, then a hospital badge | Exposure apps never knew *by whom*. Hospitals have badge data but get flat lists. |
| 0:12 to 0:30 | Load the ward, report a nurse positive on day 3 | A real ward: about 75 people, 4 days of sensor contacts, one Relate file in the browser. |
| 0:30 to 0:55 | Exposed list with direct and second-hand, export CSV | Who to test, ranked by time and minutes of contact. Second-hand only counts if the contacts happened in order. |
| 0:55 to 1:15 | Report two more cases, source ranking, click a chain | The likely source is a doctor nobody listed: backward tracing found it. |
| 1:15 to 1:35 | Evidence tab | On 50 replays, chains plus backward tracing prevented X more cases than direct-only, for Y more isolations. |
| 1:35 to 1:50 | Show Cypher, then the same query in the terminal | Every answer is a query on a file you can clone. |
| 1:50 to 2:00 | README and repo topics | Clone it, `make demo`, or just open the link. |

X, Y and the "source was a doctor" beat are placeholders until the data and runs are in.

## Graph model and key queries

Two layers share one file: the observed contact network, which never changes, and simulation runs layered on top, each tagged by run id so policies can be compared side by side.

| Element | Kind | Key properties | Notes |
| --- | --- | --- | --- |
| `Person` | Node | `id`, `role` (patient, nurse, doctor, admin) | From the ward metadata |
| `CONTACT` | Relationship, Person to Person | `start`, `end`, `duration_s`, `day` | Consecutive 20 s intervals merged into one contact episode. Query as undirected. |
| `Run` | Node | `id`, `seed`, `policy`, `beta`, `delay_h`, `created` | One per simulation |
| `INFECTED` | Relationship, Person to Person | `run`, `t`, `contact_start` | Who infected whom, in which run. Forms the true transmission tree. |
| `DETECTED` / `QUARANTINED` | Relationship, Run to Person | `t`, `reason` | What the policy saw and did |
| Investigation, EXPOSED, SOURCE\_CANDIDATE | Node, plus relationships Investigation to Person | case ids, window; on EXPOSED: t, hop, via, seconds | New in v2. Each saved investigation is written back into the file, so judges can open the answers, not just the inputs. The via pointer rebuilds the chain. |

**Why v1's queries had to change.** A busy ward produces thousands of contact episodes among about 75 people, so each person has hundreds of `CONTACT` edges. A `[:CONTACT*1..3]` pattern then enumerates every combination of edges, which can reach millions of paths before the time filter discards them. v2 uses *earliest-arrival expansion*: one hop per query, keeping only the best arrival time per person, repeated until nothing improves. It is exact, it stays fast, and every step is still a graph query.

**Q1. Who was exposed?** One expansion step. The app feeds back improved arrival times, usually 2 to 4 rounds; hop 1 is direct exposure, hop 2+ is second-hand.

```cypher
UNWIND $frontier AS f
MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person)
WHERE r.end >= f.t AND r.start <= $window_end
  AND r.duration_s >= $min_seconds
RETURN b.id AS id,
       min(CASE WHEN f.t > r.start THEN f.t ELSE r.start END) AS arrival,
       sum(r.duration_s) AS seconds
```

**Q2. Where did it come from?** The same step run backward in time from each reported case (latest departure instead of earliest arrival). People who can reach the most cases in time rank highest.

```cypher
UNWIND $frontier AS f
MATCH (b:Person {id: f.id})-[r:CONTACT]-(a:Person)
WHERE r.start <= f.t AND r.end >= $window_start
RETURN a.id AS id, f.case AS case,
       max(CASE WHEN f.t < r.end THEN f.t ELSE r.end END) AS departure
```

The loop lives in a \~40-line TypeScript/Python helper shared by the app, the CLI scripts and the tests. Results are saved as `EXPOSED` and `SOURCE_CANDIDATE` edges, so the chain view (Q3) is a short walk along `via` pointers.

**Q3. True chain for one case in one run** (the click-to-explain view).

```cypher
MATCH p = (zero:Person)-[:INFECTED*]->(x:Person {id: $id})
WHERE all(r IN relationships(p) WHERE r.run = $run)
  AND NOT ()-[:INFECTED {run: $run}]->(zero)
RETURN [n IN nodes(p) | n.id] AS chain, [r IN relationships(p) | r.t] AS times
```

**Q4. Policy shootout.** One aggregate over `Run` nodes: infections, quarantines, and quarantines per infection averted, grouped by policy across seeds.

The simulation itself (who gets infected when) can run in Python or JS; the graph does the parts that are about relationships: exposure, sources, chains, and comparison. The policy logic *is* Q1 and Q2, which is what earns the 30 points.

## Architecture and tech stack

Heavy work (import, simulation, batch policy runs) happens once in Python and lands in a single `.relate` file; the browser, CLI, and agents all read that same file.

&#91;embedded content: architecture · build in Python, explore from one file\]

The browser can also run fresh single simulations live for the play-button moment, while the 50-seed policy comparison is precomputed.

| Layer | Choice | Why |
| --- | --- | --- |
| Graph store | Relate v1.0, single-file mode | Inspectable store the rules require; one artifact to clone |
| Build scripts | Python 3.12, `relate-db`, pandas, numpy | Fast to write; `pip install relate-db` is documented |
| Browser engine | `@relate/relate-wasm` in a Web Worker | OPFS durable storage only works in a worker, so start there |
| Front end | Vite + TypeScript, plain or Svelte | Small, fast, no framework fights |
| Graph view | Sigma.js with graphology, fixed layout grouped by role | Handles \~75 nodes and thousands of edges with WebGL |
| Charts | Observable Plot | Results card and optional delay sweep |
| NL questions (stretch) | Claude API or Relate MCP server, Cypher shown before it runs | Auditable agent answers |
| Hosting | GitHub Pages | Judges can try it without cloning |
| Tooling | `uv` or `make demo` single command, GitHub Actions to rebuild the file | Reproducibility points |

## Scope

Ship the investigation flow, its tests, and the judge's path by Dec 4; everything else is optional. v2 moves repo setup, tests, CI and hosting into the MVP because three criteria (30, 25, 15 pts) score them directly.

| Tier | Feature | Est. hours |
| --- | --- | --- |
| MVP | Repo, topics, CI skeleton, Pages deploy (day one) | 2 |
| MVP | Python importer: SocioPatterns file to `data/ward.relate` (merge intervals, roles) | 5 |
| MVP | Expansion helper (Q1, Q2) in Python and TS, with tests on a 6-person toy graph with hand-checked answers | 6 |
| MVP | Investigation write-back (`Investigation`, `EXPOSED`, `SOURCE_CANDIDATE`) | 2 |
| MVP | Browser app: load file into Relate WASM in a worker, graph + scrubber, case panel, exposed list, CSV export, chain view, Show Cypher | 16 |
| MVP | Simulator + three policies + 50-seed batch, results card (evidence tab) | 9 |
| MVP | `queries/` folder of named queries, `make demo`, README to template, Devpost text, video | 8 |
| Stretch | MCP: `relate` server on the file plus a Claude Desktop config snippet, "ask the outbreak" | 3 |
| Stretch | Second dataset (SocioPatterns school or conference) to show it generalizes | 3 |
| Stretch | Tracing-delay sweep chart | 3 |
| Cut | Maps, GPS, real patient data, accounts, mobile app, NL-to-Cypher UI, custom layout engine | 0 |

MVP is about 50 hours, stretch 9: roughly 59 of a \~60-hour budget, or about 15 hours a week. **Acceptance test for "done":** on a fresh machine, a judge can reach the exposed list for a reported case in under five minutes by each of the three paths (hosted page, `make demo`, CLI).

## Timeline

Four build weeks, an MVP freeze on Dec 4, and submission on Dec 11 (deadline, confirmed by rules — 6 PM PST).

&#91;embedded content: plan · Nov 15 to Dec 10, 2026\]

Thanksgiving (Nov 26) falls in the simulator week, so the browser work starts in parallel on Nov 24. Go/no-go is on Nov 18, after the spikes.

## Validate before starting

Run these spikes Nov 15 to 18 (about 8 hours total). Spikes 1, 2 and 7 are blocking: if one fails, take its fallback; if two fail, switch ideas while there is still time.

- [ ] **Spike 1. File in the browser.** Build a small graph with `pip install relate-db`, save it as a single file, then open that same file in `@relate/relate-wasm`. The README only documents in-memory and OPFS (`opfs://`, worker only) for the browser. Need to confirm you can load a file shipped with the site, for example by fetching its bytes into OPFS. *Fallback:* ship a Cypher or JSON export next to the `.relate` file and load that into in-memory WASM; the file stays the inspectable store for the CLI.
- [ ] **Spike 2. Path queries at size.** Load the full ward data and time Q1 and Q2 in WASM. Check that `reduce` over `relationships(p)`, variable-length undirected patterns, and `1e18` floats all work. Target under 300 ms per query. *Fallback:* cap at 2 hops, pre-aggregate contacts per person-pair per day, or move Q2 into the Python batch step.
- [ ] **Spike 3. Data check.** Download the ward data from SocioPatterns, confirm the participant count, role labels, time span, and the license. Count contact episodes after merging intervals.
- [ ] **Spike 4. Read `docs/limitations.md`** in the Relate repo for anything blocking (path functions, indexes, list functions, file locking between Python writer and CLI reader).
- [ ] **Spike 5. Rules check.** Ask in the Devpost discussions or by email whether a browser app that loads a committed `.relate` file meets the persistent-store rule. Also confirm that LLM-generated code is allowed.
- [ ] **Spike 6. Duplicate check.** Search the Devpost project gallery and the relate-ideas issues for contact-tracing or epidemic entries.
- [ ] **Spike 7. Edge counts and query speed (new, blocking).** After import, count contact episodes and the busiest person's edge count. Time one Q1 expansion round and a full 4-round investigation in WASM. Target: under 1 second end to end. *Fallback:* add a per-pair-per-day `MET` summary relationship and expand over that first.
- [ ] **Spike 8. License fit (new).** The ward data is CC BY-NC-SA 3.0, so the committed `.relate` file is a derivative and must carry the same license. Put the code under MIT, the data under CC BY-NC-SA with attribution in `DATA_LICENSE`, and confirm the hackathon rules allow that split.
- [ ] **Spike 9. Cold-start rehearsal (new).** On Nov 18, have a friend clone the empty repo skeleton and run `make demo` with no help. Repeat on Dec 8 with the real build.

Also sanity-check the science early: with a single ward and \~4 days, the backward-tracing benefit may be small or noisy. Decide up front that any honest result is fine to show, including "backward tracing helped less here, and here is why."

## Risks

The biggest risk is Relate itself being three days old; everything else has a known fallback.

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| WASM can't load a shipped file, or OPFS needs worker plumbing | Medium | Spike 1 fallback (export file). Use a Web Worker from day one. |
| Path queries too slow in the browser | Medium | Pre-compute heavy runs in Python, store results in the file, keep the browser for exploring. |
| Relate bugs in a v1.0 engine | Medium | Pin the version, file issues upstream (judges are the maintainers, which is a plus), keep queries simple. |
| Graph view gets cluttered (dense ward contacts) | High | Show only active edges inside the scrubber window; use a fixed layout grouped by role. |
| Science looks naive to a judge | Low | Cite Endo et al., state assumptions in the README, keep the model simple and labeled as illustrative. |
| Health data sensitivity | Low | Data is anonymous and published for research. Note it in the README with attribution. |
| Time crunch with classes and the Jan 11 hackathon | Medium | Hard MVP freeze Dec 4. Stretch only after the video is recorded. |
| Another team builds contact tracing | Low to medium | Time-respecting paths and the policy shootout are hard to copy in a month. |
| Judge can't get it running (Node, WASM, CORS on file fetch) | Medium | Three paths in the README, hosted page first. Spike 9 rehearsals. CI proves the CLI path on every push. |
| Judges see it as a COVID throwback | Medium | Frame it as hospital-acquired infection (flu, norovirus) investigation, a standing need, not pandemic nostalgia. Mention COVID only through Immuni. |
| Evidence tab shows little benefit | Medium | The product is the investigation, so a modest result doesn't sink it. Report it honestly with the delay sweep if time allows. |

## Sources

- [Relate by Neo4j Hackathon (Devpost)](https://relate.devpost.com/)
- [relatedb/relate on GitHub](https://github.com/relatedb/relate)
- [Neo4j press release: Relate launch](https://neo4j.com/?p=435950)
- [Three ways to run Relate (GraphAcademy)](https://graphacademy.neo4j.com/blog/three-ways-to-run-relate)
- [Bending Spoons portfolio research (jexp/relate-ideas)](https://github.com/jexp/relate-ideas/blob/main/Research/bending-spoons-portfolio.md)
- [Immuni on Developers Italia](https://developers.italia.it/en/software/github.com/immuni-app/immuni)
- [Immuni technology documentation](https://github.com/immuni-app/immuni-documentation/blob/78a3a35c3751093c20a991af0395867ec16f888d/Technology.md)
- [Neo4j contact-tracing example](https://github.com/neo4j-graph-examples/contact-tracing)
- [COCOM Brussels case study](https://neo4j.com/customer-stories/cocom/)
- [Geneva contact tracing with Neo4j](https://neo4j.com/?p=143952)
- [Vanhems et al. 2013, hospital ward contacts (PLOS ONE)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3770639)
- [sp\_hospital on Netzschleuder](https://networks.skewed.de/net/sp_hospital)
- [Endo et al., backward contact tracing (Wellcome Open Research)](https://doaj.org/article/1d536a71aed0438f886d5e878dd980ef)
- [EoN documentation](https://epidemicsonnetworks.readthedocs.io/)
- [What Happens Next? (Case and Salathé)](https://ncase.me/covid-19/)
- [Midmark RTLS automated contact tracing](https://www.midmark.com/docs/default-source/product-literature/medical/rtls/info-sheet---midmark-rtls---automated-contact-tracing-act-plan.pdf)
- [CenTrak contact tracing brochure](https://content.centrak.com/hubfs/RTLS%20Brochures/Contact%20Tracing_010322.pdf)
- [Wake Forest Baptist Health RTLS contact tracing (Healthcare IT News)](https://healthcareitnews.com/node/547126)
- [RFiD Discovery contact tracing for infection control (24x7)](https://24x7mag.com/medical-equipment/software/new-rtls-based-contact-tracing-tool-targets-hospital-infection-control)
- [RTLS vs. EMR contact tracing study (JMIR, 2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7252199)
