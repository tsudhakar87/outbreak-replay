"""
Spike 7 – Time the Q1 earliest-arrival expansion on the full ward data.

Runs a full investigation (all rounds until nothing improves) from three
starting people:
  1. The busiest person (most episodes) — worst case
  2. A typical nurse
  3. A typical patient

For each, prints rounds needed, people reached per hop, and total time in ms.
Also times a single expansion round on its own.
Appends results to spikes/RESULTS.md.
"""

import pathlib
import time
import relate

DB = pathlib.Path(__file__).parent.parent / "data" / "ward.rl"

db = relate.connect(str(DB))

WINDOW_END  = 999_999_999   # no end limit
MIN_SECONDS = 1


def expand(start_id: int, start_t: int) -> dict:
    """Run full earliest-arrival expansion. Returns timing dict."""
    arrival  = {start_id: start_t}
    frontier = [{"id": start_id, "t": start_t}]
    rounds   = []
    t0 = time.perf_counter()

    while frontier:
        rows = db.execute(
            """
            UNWIND $frontier AS f
            MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person)
            WHERE r.end >= f.t AND r.start <= $window_end
              AND r.duration_s >= $min_s
            RETURN b.id AS id,
                   min(CASE WHEN f.t > r.start THEN f.t ELSE r.start END) AS arrival
            """,
            {"frontier": frontier, "window_end": WINDOW_END, "min_s": MIN_SECONDS},
        )
        new_frontier = []
        for row in rows:
            bid = row["id"]
            arr = row["arrival"]
            if bid not in arrival or arr < arrival[bid]:
                arrival[bid] = arr
                new_frontier.append({"id": bid, "t": arr})
        rounds.append(len(new_frontier))
        frontier = new_frontier

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "reached":    len(arrival) - 1,   # exclude the seed
        "rounds":     len(rounds),
        "per_round":  rounds,
        "elapsed_ms": elapsed_ms,
    }


def one_round(start_id: int, start_t: int) -> float:
    """Time a single expansion round. Returns ms."""
    frontier = [{"id": start_id, "t": start_t}]
    t0 = time.perf_counter()
    db.execute(
        """
        UNWIND $frontier AS f
        MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person)
        WHERE r.end >= f.t AND r.start <= $window_end
          AND r.duration_s >= $min_s
        RETURN b.id AS id,
               min(CASE WHEN f.t > r.start THEN f.t ELSE r.start END) AS arrival
        """,
        {"frontier": frontier, "window_end": WINDOW_END, "min_s": MIN_SECONDS},
    )
    return (time.perf_counter() - t0) * 1000


# ── Identify seed people ─────────────────────────────────────────────────────
# Busiest person from Spike 3: id=1115 (NUR), 1,667 episodes
busiest_id = 1115

# Typical nurse: pick the first NUR who is not the busiest
nurses = [
    r["id"] for r in db.execute(
        "MATCH (p:Person {role: 'NUR'}) RETURN p.id AS id ORDER BY p.id LIMIT 10"
    )
]
typical_nurse = next(n for n in nurses if n != busiest_id)

# Typical patient
typical_pat = db.execute(
    "MATCH (p:Person {role: 'PAT'}) RETURN p.id AS id ORDER BY p.id LIMIT 1"
).single()["id"]

# Start time = beginning of day 2 (86400 s into the recording)
START_T = 86400

seeds = [
    ("busiest NUR", busiest_id),
    ("typical NUR", typical_nurse),
    ("typical PAT", typical_pat),
]

results = []
print(f"{'Seed':<18} {'id':>6} {'reached':>8} {'rounds':>7} {'ms':>8}")
print("-" * 55)
for label, sid in seeds:
    r = expand(sid, START_T)
    print(f"{label:<18} {sid:>6} {r['reached']:>8} {r['rounds']:>7} {r['elapsed_ms']:>7.1f}ms"
          f"  per round: {r['per_round']}")
    results.append((label, sid, r))

# Single-round timing (busiest person, repeated for stability)
single_times = [one_round(busiest_id, START_T) for _ in range(5)]
single_avg = sum(single_times) / len(single_times)
print(f"\nSingle round (busiest, 5 runs): avg {single_avg:.1f}ms")

worst = max(r["elapsed_ms"] for _, _, r in results)
print(f"\nSlowest full investigation: {worst:.1f}ms  "
      f"({'PASS < 1000ms' if worst < 1000 else 'FAIL > 1000ms'})")

db.close()

# ── Append to RESULTS.md ─────────────────────────────────────────────────────
results_path = pathlib.Path(__file__).parent / "RESULTS.md"
lines = ["\n---\n",
         "## Spike 7 – Query speed (`spikes/time_queries.py`) — 2026-11-16\n\n"]
lines.append(f"| Seed | id | Reached | Rounds | ms |\n")
lines.append(f"|---|---|---|---|---|\n")
for label, sid, r in results:
    lines.append(f"| {label} | {sid} | {r['reached']} | {r['rounds']} | {r['elapsed_ms']:.0f} |\n")
lines.append(f"\nSingle expansion round (busiest, avg 5 runs): {single_avg:.1f} ms\n")
lines.append(f"\n**Slowest full investigation: {worst:.0f} ms — "
             f"{'PASS (< 1000 ms)' if worst < 1000 else 'FAIL (> 1000 ms)'}**\n")
lines.append(f"\nFallback needed: {'No' if worst < 1000 else 'Yes — add MET summary relationship'}\n")

with open(results_path, "a") as f:
    f.writelines(lines)
print(f"\nAppended to {results_path}")
