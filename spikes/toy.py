"""
Spike 2 – Core query on the toy graph.

Six-person graph with one time-ordering trap:
  C–D contact at [5,8] ended BEFORE C was exposed (t=30).
  A naive (time-ignoring) traversal would reach D at t=5 via C.
  The correct earliest-arrival expansion must yield D=100 (direct from A).

Contact table (matches spikes/checklist exactly):
  A–B  [10, 20]
  B–E  [15, 25]   ← E is second-hand via B, not direct from A
  B–C  [30, 40]
  C–D  [ 5,  8]   ← TRAP: C met D before C was exposed
  E–F  [50, 60]
  A–D  [100,110]  ← only valid path to D

Expected arrivals (excluding index case A):
  B=10, E=15, C=30, F=50, D=100

Usage:
  python spikes/toy.py
Then verify the file from the CLI:
  relate query "MATCH (a:Person)-[r:CONTACT]-(b:Person) RETURN a.id, b.id, r.start, r.end ORDER BY r.start" --database spikes/toy.relate
"""

import pathlib
import relate

DB = pathlib.Path(__file__).parent / "toy.rl"
# .rl = single-file bundle; .relate (no extension) = directory database
import shutil
if DB.exists():
    shutil.rmtree(DB) if DB.is_dir() else DB.unlink()

# ── Build the graph ───────────────────────────────────────────────────────────
print("Building toy graph …")
db = relate.connect(str(DB))

for pid, role in [("A","index"), ("B","staff"), ("C","staff"),
                  ("D","patient"), ("E","staff"), ("F","patient")]:
    db.execute("CREATE (:Person {id: $id, role: $role})", {"id": pid, "role": role})

contacts = [
    # (id_a, id_b, start, end)  — matches checklist table exactly
    ("A", "B",   10,  20),   # A exposes B at t=10 (hop 1)
    ("B", "E",   15,  25),   # B (exposed@10) exposes E at t=15 (hop 2)
    ("B", "C",   30,  40),   # B (exposed@10) exposes C at t=30 (hop 2)
    ("C", "D",    5,   8),   # TRAP: C met D before C was exposed; r.end=8 < C.arrival=30
    ("E", "F",   50,  60),   # E (exposed@15) exposes F at t=50 (hop 3)
    ("A", "D",  100, 110),   # only valid path to D: direct from A at t=100
]
for a, b, start, end in contacts:
    db.execute(
        "MATCH (a:Person {id: $a}), (b:Person {id: $b}) "
        "CREATE (a)-[:CONTACT {start: $s, end: $e, duration_s: $dur}]->(b)",
        {"a": a, "b": b, "s": start, "e": end, "dur": end - start},
    )

db.close()
print(f"Wrote and closed {DB}\n")

# ── Reopen and run earliest-arrival expansion ─────────────────────────────────
print("Reopening from disk …")
db = relate.connect(str(DB))

WINDOW_END  = 200   # search window end
MIN_SECONDS = 1     # minimum contact duration filter (seconds)

arrival  = {"A": 0}                     # index case
frontier = [{"id": "A", "t": 0}]
rnd      = 0

while frontier:
    rnd += 1
    rows = db.execute(
        """
        UNWIND $frontier AS f
        MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person)
        WHERE r.end >= f.t
          AND r.start <= $window_end
          AND r.duration_s >= $min_s
        RETURN b.id AS id,
               min(CASE WHEN f.t > r.start THEN f.t ELSE r.start END) AS arrival,
               sum(r.duration_s) AS seconds
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

    ids = [f["id"] for f in new_frontier]
    print(f"  round {rnd}: new/improved → {ids if ids else '(none)'}")
    frontier = new_frontier

db.close()

# ── Results ───────────────────────────────────────────────────────────────────
print("\nArrival times:")
for pid in sorted(arrival):
    marker = " ← index" if pid == "A" else ""
    print(f"  {pid}: {arrival[pid]}{marker}")

# ── Assertions ────────────────────────────────────────────────────────────────
expected = {"B": 10, "E": 15, "C": 30, "F": 50, "D": 100}
print("\nAssertions:")
failures = []
for pid, exp in sorted(expected.items()):
    got = arrival.get(pid)
    ok  = got == exp
    print(f"  {pid}: expected={exp}  got={got}  {'OK' if ok else 'FAIL <---'}")
    if not ok:
        failures.append(pid)

print()
if failures:
    print(f"FAIL — wrong arrivals for: {failures}")
    raise SystemExit(1)
else:
    print("PASS")

print(f"\nCLI check (run this yourself):")
print(f"  relate query \"MATCH (a:Person)-[r:CONTACT]-(b:Person) RETURN a.id, b.id, r.start, r.end ORDER BY r.start\" --database {DB}")
