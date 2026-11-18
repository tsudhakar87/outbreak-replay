# Outbreak Replay

Outbreak Replay is a ward exposure investigator for hospital infection-prevention teams: given a positive case, it returns who was exposed (with time and duration), the likely source, and the time-ordered transmission chain, all from contact data stored in a single Relate graph file (`data/ward.rl`). It uses the SocioPatterns Lyon hospital ward dataset (face-to-face contacts among ~75 patients and staff, logged in 20-second intervals) and adds time-respecting path queries and a policy comparison that flat badge-system reports cannot provide.

## Folder layout

- `spikes/` — throwaway validation scripts, one subdirectory per spike (e.g. `spikes/01-file-in-browser/`); results go in `spikes/RESULTS.md`
- `data/` — raw source files and the built `ward.relate` graph file
- `docs/` — planning documents (plan.md, etc.)

## Working rules

1. **We are in spike phase.** No app code yet. The goal right now is to validate the blocking assumptions (Relate file loading in the browser, query speed at size, data licensing) before building anything.
2. **Spike code goes in `spikes/`.** Each spike gets its own subdirectory. Keep scripts short and focused; they are throwaway.
3. **Record every result in `spikes/RESULTS.md`.** Note what passed, what failed, timings, and any fallback decisions made.
4. **Always load the `relate` skill and read its docs before guessing any Relate API.** Relate is days old (launched Nov 11, 2026); do not assume Neo4j Cypher compatibility or CLI flags — verify them from the skill or the upstream docs first.
