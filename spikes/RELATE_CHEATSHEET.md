# Relate Cheat Sheet

Verified against Relate v1.0.1 / v1.0.2, Nov 2026. Sources: installed skill
(`relate skill check`), `docs/limitations.md`, `docs/api/python/spec.md`,
`docs/api/wasm/spec.md`.

---

## Open a single-file database

### CLI

```bash
# One-shot query
relate query "MATCH (p:Person) RETURN count(p)" --database data/ward.relate

# Script from stdin
relate query --database data/ward.relate < queries/exposed.cypher

# Interactive REPL
relate --database data/ward.relate
```

There is **no `-f` flag** for a Cypher file; pipe via stdin instead.
Short form: `-d` is an alias for `--database`.

### Python

```python
import relate

db = relate.connect("data/ward.relate")          # single .rl file
db = relate.connect("data/ward/")                # directory database
db = relate.connect(":memory:")                  # ephemeral

# Parameterised query
rows = db.execute(
    "UNWIND $frontier AS f MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person) "
    "WHERE r.end >= f.t RETURN b.id AS id, min(r.start) AS arrival",
    {"frontier": [{"id": 1115, "t": 86400}]},
)
for row in rows:
    print(row["id"], row["arrival"])

db.close()
```

Pass parameters as a plain Python `dict`; every referenced `$name` must be
present (a missing key fails with `ParameterMissing`, never binds `null`).
One writer process at a time; open read-only beside a writer:
`relate.connect("data/ward.relate", read_only=True)`.

### Browser / WASM

OPFS is **worker-only**. In-memory may run on the page thread.

```ts
// In a Web Worker only:
import init, { RelateDb } from "@relate/relate-wasm";
import wasmUrl from "@relate/relate-wasm/relate_bg.wasm?url";  // Vite

await init(wasmUrl);                           // must come first

// In-memory (page thread or worker)
const db = new RelateDb();

// OPFS durable store (worker only)
const db = await RelateDb.open("opfs://ward"); // name: [A-Za-z0-9_-], ≤64 chars

// Execute
const result = JSON.parse(db.execute(
    "MATCH (p:Person) RETURN count(p) AS n",
    null                                       // null = no params
));
// result.columns / result.rows / result.error (check this — errors don't throw)

// With params
const result2 = JSON.parse(db.execute(
    "UNWIND $frontier AS f MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person) RETURN b.id AS id",
    JSON.stringify({ frontier: [{ id: 1115, t: 86400 }] })
));
```

**Loading an existing `.relate` file in the browser:**
The WASM docs do not describe a direct byte-import API. The expected approach
(Spike 1 to confirm) is:
- Route 1: fetch the `.rl` bytes → write into OPFS via `FileSystemSyncAccessHandle`
  → `RelateDb.open("opfs://ward")`. UNCONFIRMED whether Relate recognises the
  written bytes as a valid store.
- Route 2 (fallback): export from Python to JSON/JSONL, load into an in-memory
  `RelateDb` via batched `UNWIND ... CREATE`. Confirmed safe.

---

## Create an index

```cypher
CREATE INDEX person_id FOR (p:Person) ON (p.id);

-- Confirm
SHOW INDEXES;
```

Unique constraint (also creates an index):
```cypher
CREATE CONSTRAINT person_id_unique FOR (p:Person) REQUIRE p.id IS UNIQUE;
```

---

## Limitations relevant to this project

| Feature | Status | Notes |
|---|---|---|
| Variable-length paths `*1..N` | Supported, max **500 hops** by default | Raise with `--max-traversal-depth`; WASM stack limits >2000 |
| Unbounded `*` | Supported, stops at **32 hops** | Not covered by traversal depth limit |
| `UNWIND` with list of maps | Supported | Expression memory cap 256 MiB per allocation (not an issue at ward scale) |
| `min` / `max` / `sum` aggregations | Supported | No limitations at ward scale |
| `CASE WHEN … THEN … ELSE … END` | Supported | Used in Q1/Q2 arrival calculation |
| `reduce` accumulator | Supported | Nesting cap 500 levels; flat scalar accumulators are fine |
| File locking | One writer process at a time | `.rl` read-only requires no active writer; `--read-only=live` is directory-only |
| WASM snapshot codec | JSON only | No Parquet; no background checkpointing |

---

## CLI flags reference

```
relate query [STATEMENT] --database PATH
  --json          one JSON object (compact when piped)
  --jsonl         one JSON object per line
  --csv           CSV output
  --markdown      Markdown table
  --mode envelope columns + types + rows + truncated per statement
  --param N=V     pass a scalar parameter (repeatable)
  --max-rows N    row cap (0 = all); default 100 in agent mode
  --timeout DUR   e.g. 10s, 500ms, 2m; exit 7 on timeout
  --read-only     refuse writes
  -d / --database PATH
```

Exit codes: 0 success · 1 runtime error · 5 conflict/locked · 6 syntax error · 7 timeout.
