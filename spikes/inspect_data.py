"""
Spike 3 – Data check.
Reads data/raw/hospital_lyon_contacts.dat and prints summary statistics.
Columns: time_s  id_a  id_b  role_a  role_b  (tab-separated, no header)
"""

import pathlib
import pandas as pd

RAW = pathlib.Path(__file__).parent.parent / "data" / "raw" / "hospital_lyon_contacts.dat"

df = pd.read_csv(RAW, sep="\t", header=None,
                 names=["time_s", "id_a", "id_b", "role_a", "role_b"])

# ── Basic counts ──────────────────────────────────────────────────────────────
print(f"Total rows:        {len(df):,}")

people_a = df[["id_a", "role_a"]].rename(columns={"id_a": "id", "role_a": "role"})
people_b = df[["id_b", "role_b"]].rename(columns={"id_b": "id", "role_b": "role"})
people = pd.concat([people_a, people_b]).drop_duplicates("id").set_index("id")

print(f"Unique people:     {len(people)}")
print("People per role:")
for role, count in people["role"].value_counts().items():
    print(f"  {role}: {count}")

# ── Time span ─────────────────────────────────────────────────────────────────
t_first = df["time_s"].min()
t_last  = df["time_s"].max()
span_h  = (t_last - t_first) / 3600
print(f"First timestamp:   {t_first} s")
print(f"Last timestamp:    {t_last} s")
print(f"Span:              {span_h:.2f} h")

# ── Distinct pairs ────────────────────────────────────────────────────────────
# Normalise so the smaller id is always first (undirected)
pair_a = df[["time_s", "id_a", "id_b"]].copy()
mask = pair_a["id_a"] > pair_a["id_b"]
pair_a.loc[mask, ["id_a", "id_b"]] = pair_a.loc[mask, ["id_b", "id_a"]].values

distinct_pairs = pair_a.groupby(["id_a", "id_b"]).ngroups
print(f"Distinct pairs:    {distinct_pairs:,}")

# ── Episode merging ───────────────────────────────────────────────────────────
# Sort each pair's contacts by time; a gap > 20 s starts a new episode.
pair_a_sorted = pair_a.sort_values(["id_a", "id_b", "time_s"])
pair_a_sorted["prev_time"] = pair_a_sorted.groupby(["id_a", "id_b"])["time_s"].shift(1)
pair_a_sorted["new_episode"] = (
    pair_a_sorted["prev_time"].isna() |
    ((pair_a_sorted["time_s"] - pair_a_sorted["prev_time"]) > 20)
)
total_episodes = pair_a_sorted["new_episode"].sum()
print(f"Contact episodes:  {total_episodes:,}")

# ── Busiest person ────────────────────────────────────────────────────────────
# Count episodes for each person (they appear as either endpoint of a pair).
ep_df = pair_a_sorted[pair_a_sorted["new_episode"]].copy()

counts_a = ep_df.groupby("id_a").size()
counts_b = ep_df.groupby("id_b").size()
person_episodes = counts_a.add(counts_b, fill_value=0).astype(int)

busiest_id    = person_episodes.idxmax()
busiest_count = person_episodes.max()
busiest_role  = people.loc[busiest_id, "role"]
print(f"Busiest person:    id={busiest_id} ({busiest_role}), {busiest_count} episodes")
