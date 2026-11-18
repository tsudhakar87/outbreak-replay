/**
 * Relate WASM worker — all database work happens here.
 * OPFS (durable storage) is only available in a dedicated worker.
 */
import init, { RelateDb } from "@relate/relate-wasm";
import wasmUrl from "@relate/relate-wasm/relate_bg.wasm?url";

let db: RelateDb | null = null;

function query(cypher: string, params: Record<string, unknown> | null = null) {
  if (!db) throw new Error("DB not ready");
  const raw = db.execute(cypher, params ? JSON.stringify(params) : null);
  const result = JSON.parse(raw);
  if (result.error) throw new Error(result.error);
  return result;
}

async function setup() {
  await init(wasmUrl);
  db = new RelateDb(); // in-memory for Step A
  self.postMessage({ type: "ready" });
}

self.addEventListener("message", async (e) => {
  const { id, cmd, payload } = e.data;
  try {
    let result;

    if (cmd === "hello") {
      result = query("RETURN 1 AS ok");

    } else if (cmd === "load-opfs") {
      // Step B Route 1: fetch ward.rl bytes, seed OPFS, open it
      const resp = await fetch("/ward.rl");
      if (!resp.ok) throw new Error(`fetch failed: ${resp.status}`);
      const bytes = await resp.arrayBuffer();

      const root = await navigator.storage.getDirectory();
      const fh = await root.getFileHandle("ward.rl", { create: true });
      const writable = await (fh as any).createSyncAccessHandle();
      writable.write(new Uint8Array(bytes));
      writable.flush();
      writable.close();

      db?.close?.();
      db = await RelateDb.open("opfs://ward.rl");
      result = query("MATCH (p:Person) RETURN count(p) AS n");

    } else if (cmd === "load-json") {
      // Step B Route 2: load from exported ward.json into in-memory DB
      const resp = await fetch("/ward.json");
      if (!resp.ok) throw new Error(`fetch failed: ${resp.status}`);
      const { people, contacts } = await resp.json() as {
        people: { id: number; role: string }[];
        contacts: { a: number; b: number; start: number; end: number; duration_s: number; day: number }[];
      };

      db?.close?.();
      db = new RelateDb();

      // Batch people
      const BATCH = 500;
      for (let i = 0; i < people.length; i += BATCH) {
        query("UNWIND $rows AS r CREATE (:Person {id: r.id, role: r.role})",
              { rows: people.slice(i, i + BATCH) });
      }
      // Batch contacts
      for (let i = 0; i < contacts.length; i += BATCH) {
        query(`UNWIND $rows AS r
               MATCH (a:Person {id: r.a}), (b:Person {id: r.b})
               CREATE (a)-[:CONTACT {start: r.s, end: r.e, duration_s: r.dur, day: r.day}]->(b)`,
              { rows: contacts.slice(i, i + BATCH).map(c =>
                  ({ a: c.a, b: c.b, s: c.start, e: c.end, dur: c.duration_s, day: c.day })) });
      }
      result = query("MATCH (p:Person) RETURN count(p) AS n, count{()-[:CONTACT]->()} AS rels");

    } else if (cmd === "investigate") {
      // Step C: earliest-arrival expansion from busiest person
      const { startId, startT } = payload as { startId: number; startT: number };
      const t0 = performance.now();

      const arrival: Record<number, number> = { [startId]: startT };
      let frontier = [{ id: startId, t: startT }];
      let rounds = 0;

      while (frontier.length) {
        const res = query(
          `UNWIND $frontier AS f
           MATCH (a:Person {id: f.id})-[r:CONTACT]-(b:Person)
           WHERE r.end >= f.t AND r.start <= $windowEnd AND r.duration_s >= 1
           RETURN b.id AS id,
                  min(CASE WHEN f.t > r.start THEN f.t ELSE r.start END) AS arrival`,
          { frontier, windowEnd: 999_999_999 }
        );
        const next: { id: number; t: number }[] = [];
        for (const row of res.rows) {
          const { id, arrival: arr } = row as { id: number; arrival: number };
          if (!(id in arrival) || arr < arrival[id]) {
            arrival[id] = arr;
            next.push({ id, t: arr });
          }
        }
        frontier = next;
        rounds++;
      }

      const elapsed = performance.now() - t0;
      result = { reached: Object.keys(arrival).length - 1, rounds, elapsed_ms: elapsed };

    } else {
      throw new Error(`Unknown cmd: ${cmd}`);
    }

    self.postMessage({ id, ok: true, result });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    self.postMessage({ id, ok: false, error: msg });
  }
});

setup().catch((err) =>
  self.postMessage({ type: "error", error: String(err) })
);
