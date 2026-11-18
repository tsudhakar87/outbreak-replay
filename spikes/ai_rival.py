"""
Spike 10 – AI agent plays the toy ward investigation.

An LLM agent opens spikes/toy.rl with the relate package and exposes
three tools, each implemented as a parameterised Cypher query:

  observe(person)              -> that person's CONTACT edges (row-limited)
  scan(person)                 -> whether they were infected (hard-coded: B, E, F)
  pin_string(from, to, start)  -> records the claim in a list

Goal given to the model: A was infected at minute 0 and becomes contagious
10 minutes after infection. Reconstruct who infected B, E, and F, and on
which meeting. Budget: at most 3 observes, 4 scans, 15 total tool calls.

Every tool call prints the Cypher it ran. Final strings are printed at the end.

Usage:
  export ANTHROPIC_API_KEY=...
  python spikes/ai_rival.py
"""

import json
import os
import pathlib
import relate
import anthropic

DB_PATH = str(pathlib.Path(__file__).parent / "toy.rl")
INFECTED = {"B", "E", "F"}        # ground truth (hidden from model)
CONTAGION_DELAY = 10               # minutes; A contagious from t=10

# ── Tool definitions ─────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "observe",
        "description": (
            "Reveal all meetings a person had. Returns their CONTACT edges "
            "with start, end, and the other person's id. Costs 1 observe use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person id (A–F)"}
            },
            "required": ["person"],
        },
    },
    {
        "name": "scan",
        "description": (
            "Tell you whether a person was infected (true/false). "
            "Does NOT reveal when they were infected. Costs 1 scan use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person id (A–F)"}
            },
            "required": ["person"],
        },
    },
    {
        "name": "pin_string",
        "description": (
            "Record your theory that `from_person` infected `to_person` "
            "at the meeting that started at `contact_start`. "
            "Only valid if from_person was contagious by contact_start "
            "(infected + 10 min delay). Free to use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_person":    {"type": "string"},
                "to_person":      {"type": "string"},
                "contact_start":  {"type": "integer", "description": "Meeting start time in minutes"},
            },
            "required": ["from_person", "to_person", "contact_start"],
        },
    },
]

# ── Tool implementations ──────────────────────────────────────────────────────
def _run(db, cypher, params=None):
    """Execute Cypher and return rows as list of dicts, printing the query."""
    print(f"    [Cypher] {cypher.strip()}")
    if params:
        print(f"    [Params] {params}")
    return [dict(r) for r in db.execute(cypher, params or {})]


def tool_observe(db, person):
    rows = _run(
        db,
        "MATCH (p:Person {id: $id})-[r:CONTACT]-(q:Person) "
        "RETURN q.id AS other, r.start AS start, r.end AS end "
        "ORDER BY r.start LIMIT 25",
        {"id": person},
    )
    return rows


def tool_scan(person):
    return {"person": person, "infected": person in INFECTED}


def tool_pin_string(strings, from_person, to_person, contact_start):
    strings.append({
        "from": from_person,
        "to":   to_person,
        "at":   contact_start,
    })
    return {"pinned": True, "total_strings": len(strings)}


# ── Agent loop ────────────────────────────────────────────────────────────────
def run():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    db = relate.connect(DB_PATH)
    client = anthropic.Anthropic(api_key=api_key)
    strings = []
    observes_left = 3
    scans_left    = 4
    total_calls   = 0
    MAX_CALLS     = 15

    system = (
        "You are a disease investigator. Person A tested positive at minute 0 "
        "and becomes contagious 10 minutes after infection (so contagious from minute 10). "
        f"The infected people are hidden; use scan to find them. "
        "Your goal: reconstruct exactly who infected B, E, and F, and at which meeting. "
        f"Budget: {observes_left} observes, {scans_left} scans, unlimited pin_string, "
        f"{MAX_CALLS} total tool calls. "
        "A meeting can only carry infection if the infector was already contagious "
        "(infected time + 10 min delay) before the meeting ended."
    )

    messages = [
        {"role": "user", "content": "Begin your investigation. A was infected at minute 0."}
    ]

    print("=" * 60)
    print("AI rival investigating the toy ward...")
    print("=" * 60)

    while total_calls < MAX_CALLS:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Collect assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            print("\n[Agent finished without calling finish tool]")
            break

        if response.stop_reason != "tool_use":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            total_calls += 1
            name  = block.name
            args  = block.input
            print(f"\nTool call {total_calls}: {name}({args})")

            if name == "observe":
                if observes_left <= 0:
                    result = {"error": "No observe uses left."}
                else:
                    observes_left -= 1
                    result = tool_observe(db, args["person"])
                    print(f"    -> {result}")

            elif name == "scan":
                if scans_left <= 0:
                    result = {"error": "No scan uses left."}
                else:
                    scans_left -= 1
                    result = tool_scan(args["person"])
                    print(f"    -> {result}")

            elif name == "pin_string":
                result = tool_pin_string(
                    strings,
                    args["from_person"],
                    args["to_person"],
                    args["contact_start"],
                )
                print(f"    -> {result}")

            else:
                result = {"error": f"Unknown tool: {name}"}

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     json.dumps(result),
            })

            if total_calls >= MAX_CALLS:
                break

        messages.append({"role": "user", "content": tool_results})

    db.close()

    print("\n" + "=" * 60)
    print(f"Agent finished. Tool calls used: {total_calls}/{MAX_CALLS}")
    print(f"Observes left: {observes_left}/3  Scans left: {scans_left}/4")
    print("\nFinal strings (agent's reconstruction):")
    if strings:
        for s in strings:
            print(f"  {s['from']} → {s['to']} at minute {s['at']}")
    else:
        print("  (none)")

    # Score: correct if the string matches a known transmission and meeting
    # Ground truth from toy graph: A→B at 10, B→E at 15, B→C at 30, E→F at 50
    ground_truth = {("A","B",10), ("B","E",15), ("E","F",50)}
    correct = sum(
        1 for s in strings
        if (s["from"], s["to"], s["at"]) in ground_truth
    )
    print(f"\nScore: {correct}/{len(ground_truth)} correct links")
    print("=" * 60)


if __name__ == "__main__":
    run()
