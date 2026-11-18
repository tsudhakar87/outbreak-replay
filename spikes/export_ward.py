"""
Exports data/ward.rl to spikes/web/public/ward.json for browser Route 2 fallback.
Format: { people: [{id, role}], contacts: [{a, b, start, end, duration_s, day}] }
"""
import json, pathlib, relate

DB  = pathlib.Path(__file__).parent.parent / "data" / "ward.rl"
OUT = pathlib.Path(__file__).parent / "web" / "public" / "ward.json"

db = relate.connect(str(DB))

people = [{"id": r["id"], "role": r["role"]}
          for r in db.execute("MATCH (p:Person) RETURN p.id AS id, p.role AS role")]

contacts = [{"a": r["a"], "b": r["b"], "start": r["start"], "end": r["end"],
             "duration_s": r["dur"], "day": r["day"]}
            for r in db.execute(
                "MATCH (a:Person)-[r:CONTACT]->(b:Person) "
                "RETURN a.id AS a, b.id AS b, r.start AS start, r.end AS end, "
                "r.duration_s AS dur, r.day AS day")]

db.close()

OUT.write_text(json.dumps({"people": people, "contacts": contacts}))
size_kb = OUT.stat().st_size / 1024
print(f"Wrote {OUT}  ({size_kb:.0f} KB, {len(people)} people, {len(contacts)} contacts)")
