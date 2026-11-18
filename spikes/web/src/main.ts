const status = document.getElementById("status")!;
const out    = document.getElementById("out")!;
const btnHello       = document.getElementById("btn-hello")       as HTMLButtonElement;
const btnCount       = document.getElementById("btn-count")       as HTMLButtonElement;
const btnInvestigate = document.getElementById("btn-investigate") as HTMLButtonElement;

let seq = 0;
const pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>();

const worker = new Worker(new URL("./db.worker.ts", import.meta.url), { type: "module" });

worker.addEventListener("message", (e) => {
  const { type, id, ok, result, error } = e.data;
  if (type === "ready") {
    status.innerHTML = `<span class="ok">Worker ready — Relate WASM loaded</span>`;
    btnHello.disabled = false;
    btnCount.disabled = false;
    btnInvestigate.disabled = false;
    return;
  }
  if (type === "error") {
    status.innerHTML = `<span class="err">Worker init error: ${error}</span>`;
    return;
  }
  const p = pending.get(id);
  if (!p) return;
  pending.delete(id);
  if (ok) p.resolve(result);
  else     p.reject(new Error(error));
});

function call(cmd: string, payload?: unknown): Promise<unknown> {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, cmd, payload });
  });
}

function log(msg: string) {
  out.textContent += msg + "\n";
}

btnHello.addEventListener("click", async () => {
  out.textContent = "";
  try {
    const r = await call("hello") as { rows: { ok: number }[] };
    log(`Step A — RETURN 1 AS ok`);
    log(`  result: ${JSON.stringify(r.rows)}`);
    log(r.rows[0]?.ok === 1 ? "  ✓ PASS" : "  ✗ FAIL");
  } catch (e) {
    log(`  ERROR: ${e}`);
  }
});

btnCount.addEventListener("click", async () => {
  out.textContent = "";
  log("Step B — loading ward data...");

  // Try Route 1 (OPFS) first
  try {
    log("  Trying Route 1: fetch ward.rl → OPFS → RelateDb.open");
    const r = await call("load-opfs") as { rows: { n: number }[] };
    log(`  Person count: ${r.rows[0]?.n} (expected 75)`);
    log(r.rows[0]?.n === 75 ? "  ✓ Route 1 PASS" : "  ✗ Route 1 wrong count");
    return;
  } catch (e) {
    log(`  Route 1 failed: ${e}`);
    log("  Trying Route 2: load ward.json into in-memory DB");
  }

  // Fall back to Route 2 (JSON)
  try {
    const r = await call("load-json") as { rows: { n: number; rels: number }[] };
    const row = r.rows[0];
    log(`  Person count: ${row?.n} (expected 75)`);
    log(`  CONTACT rels: ${row?.rels} (expected 14037)`);
    log(row?.n === 75 && row?.rels === 14037 ? "  ✓ Route 2 PASS" : "  ✗ Route 2 wrong counts");
  } catch (e) {
    log(`  Route 2 also failed: ${e}`);
  }
});

btnInvestigate.addEventListener("click", async () => {
  out.textContent = "";
  log("Step C — running investigation from busiest person (id=1115, t=86400s)...");
  try {
    const t0 = performance.now();
    const r = await call("investigate", { startId: 1115, startT: 86400 }) as {
      reached: number; rounds: number; elapsed_ms: number;
    };
    const wall = performance.now() - t0;
    log(`  Reached: ${r.reached} people`);
    log(`  Rounds:  ${r.rounds}`);
    log(`  WASM time:  ${r.elapsed_ms.toFixed(1)} ms`);
    log(`  Wall time:  ${wall.toFixed(1)} ms`);
    log(r.reached === 68 ? "  ✓ count matches Python (68)" : `  ✗ expected 68, got ${r.reached}`);
    log(r.elapsed_ms < 1000 ? "  ✓ PASS < 1000 ms" : "  ✗ FAIL > 1000 ms");
  } catch (e) {
    log(`  ERROR: ${e}`);
  }
});
