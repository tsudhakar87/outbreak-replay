"""
Spike 7 – Import the real ward data into a Relate single-file database.

Reads data/raw/hospital_lyon_contacts.dat, merges consecutive 20-second
intervals into contact episodes, and writes:
  (:Person {id, role})
  (:Person)-[:CONTACT {start, end, duration_s, day}]->(:Person)

Batches writes with UNWIND. Prints import time, file size, and counts.
"""

import pathlib
import time
import relate
import pandas as pd

RAW = pathlib.Path(__file__).parent.parent / "data" / "raw" / "hospital_lyon_contacts.dat"
DB  = pathlib.Path(__file__).parent.parent / "data" / "ward.rl"
# .rl = single-file bundle (required for browser shipping and CLI portability)

import shutil
if DB.exists():
    shutil.rmtree(DB) if DB.is_dir() else DB.unlink()
print(f"Importing {RAW} → {DB}")

# ── Load and merge episodes (same logic as inspect_data.py) ──────────────────
df = pd.read_csv(RAW, sep="\t", header=None,
                 names=["time_s", "id_a", "id_b", "role_a", "role_b"])

# Normalise pair direction so smaller id is always first
mask = df["id_a"] > df["id_b"]
df.loc[mask, ["id_a", "id_b"]] = df.loc[mask, ["id_b", "id_a"]].values
df.loc[mask, ["role_a", "role_b"]] = df.loc[mask, ["role_b", "role_a"]].values

df_sorted = df.sort_values(["id_a", "id_b", "time_s"])
df_sorted["prev_time"] = df_sorted.groupby(["id_a", "id_b"])["time_s"].shift(1)
df_sorted["new_ep"] = (
    df_sorted["prev_time"].isna() |
    ((df_sorted["time_s"] - df_sorted["prev_time"]) > 20)
)
df_sorted["ep_id"] = df_sorted["new_ep"].cumsum()

episodes = (
    df_sorted.groupby(["id_a", "id_b", "ep_id", "role_a", "role_b"])
    .agg(start=("time_s", "min"), end=("time_s", "max"))
    .reset_index()
)
# duration = end - start + 20 (each reading covers a 20-second window)
episodes["duration_s"] = (episodes["end"] - episodes["start"] + 20).astype(int)
episodes["start"]      = episodes["start"].astype(int)
episodes["end"]        = episodes["end"].astype(int)
# day number (0-based, seconds / 86400)
episodes["day"]        = (episodes["start"] // 86400).astype(int)

print(f"  Episodes to import:  {len(episodes):,}")

# ── Collect unique people ────────────────────────────────────────────────────
people_a = df[["id_a", "role_a"]].rename(columns={"id_a": "id", "role_a": "role"})
people_b = df[["id_b", "role_b"]].rename(columns={"id_b": "id", "role_b": "role"})
people   = pd.concat([people_a, people_b]).drop_duplicates("id")
people_list = [{"id": int(r.id), "role": r.role} for r in people.itertuples()]
print(f"  People to import:    {len(people_list)}")

# ── Write to Relate ──────────────────────────────────────────────────────────
t0 = time.perf_counter()
db = relate.connect(str(DB))

# Index on Person.id for fast lookups
db.execute("CREATE INDEX person_id FOR (p:Person) ON (p.id)")

# Batch-insert people
BATCH = 500
for i in range(0, len(people_list), BATCH):
    chunk = people_list[i : i + BATCH]
    db.execute(
        "UNWIND $rows AS r CREATE (:Person {id: r.id, role: r.role})",
        {"rows": chunk},
    )

# Batch-insert contact episodes
ep_rows = [
    {
        "a":   int(r.id_a),
        "b":   int(r.id_b),
        "s":   r.start,
        "e":   r.end,
        "dur": r.duration_s,
        "day": r.day,
    }
    for r in episodes.itertuples()
]
for i in range(0, len(ep_rows), BATCH):
    chunk = ep_rows[i : i + BATCH]
    db.execute(
        """
        UNWIND $rows AS r
        MATCH (a:Person {id: r.a}), (b:Person {id: r.b})
        CREATE (a)-[:CONTACT {start: r.s, end: r.e,
                               duration_s: r.dur, day: r.day}]->(b)
        """,
        {"rows": chunk},
    )

db.close()
t1 = time.perf_counter()

# ── Stats ────────────────────────────────────────────────────────────────────
size_mb = DB.stat().st_size / 1_048_576
print(f"\nImport complete in {t1 - t0:.1f}s")
print(f"File size: {size_mb:.1f} MB")

# Verify counts
db2 = relate.connect(str(DB))
n_people = db2.execute("MATCH (p:Person) RETURN count(p) AS n").single()["n"]
n_contacts = db2.execute("MATCH ()-[r:CONTACT]->() RETURN count(r) AS n").single()["n"]
db2.close()

print(f"Person nodes: {n_people}  (expected 75)")
print(f"CONTACT rels: {n_contacts:,}  (expected {len(episodes):,})")
assert n_people == 75,          f"Person count wrong: {n_people}"
assert n_contacts == len(episodes), f"Episode count wrong: {n_contacts}"
print("Counts match. PASS")
