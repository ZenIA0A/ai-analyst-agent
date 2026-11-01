"""Study 2. Three questions study 1 left open:
  B2  Does the original agent (4 tools) still hold up on 30 harder questions?            (hard set only)
  E   Does an agent with counting/ranking tools and a derivation verifier do better?     (all 108 questions)
  D   Is a tool loop needed at all, or is it enough to paste the tables into the prompt? (all 108 questions, no tools)
Every call is logged to outputs/runs2_<model>.jsonl. Resumable: finished items are skipped."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from llm import call_llm
from tools import catalog_text, TOOL_HELP2, TOOLS, TOOLS2, TABLES, COLUMNS, run_tool
from scoring import verify
from run_eval import BASE_RULES, INJECTION_RULE, make_prompt, parse_json, agent_system

MAX_TOOLS = 6
Q1 = json.load(open("outputs/questions.json")); Q2 = json.load(open("outputs/questions_hard.json"))
for q in Q1: q["set"] = "original"
for q in Q2: q["set"] = "hard"

E_RULES = BASE_RULES.replace("{RULE3}", INJECTION_RULE.replace("4. ", "4. Use count_where, max_change and rank_groups for counts, largest changes and rankings; do not scan rows by eye.\n5. In your final answer add a field \"derivation\": \"step N\" if the value is read directly from the result of step N, or the arithmetic expression that produces it, using numbers copied from data-tool results.\n6. "))
E_SYSTEM = E_RULES + "\n\nTOOLS\n" + TOOL_HELP2 + "\n\nTABLES\n" + catalog_text()

def tables_csv():
    out = []
    for t, cols in COLUMNS.items():
        d = TABLES[t]
        d = d[["group"] + list(cols)] if t == "apra_quarterly" else d[list(cols)]
        out.append(f"### TABLE {t}\n" + d.round(4).to_csv(date_format="%Y-%m-%d"))
    return "\n".join(out)
D_SYSTEM = ("You are a careful data analyst assistant for a bank's credit-risk team. The complete tables are given below as CSV, with a description of every column. "
            "Answer using ONLY these tables. Work carefully: for counts, maxima and rankings check every row.\n"
            "If the tables cannot answer the question (data missing or masked, a future period, an entity or variable that is not in the tables, a forecast), reply with can_answer false. Do not guess.\n"
            "Reply with exactly one JSON object and nothing else: {\"can_answer\": true or false, \"value\": <number, text or null>, \"unit\": \"<unit>\", \"explanation\": \"<one short sentence>\"}\n"
            "For date answers give value as YYYY-MM-DD. For lender-group answers use the exact group name. Give numbers in the unit the question asks for.\n\n"
            "COLUMN DESCRIPTIONS\n" + catalog_text() + "\n\nDATA\n" + tables_csv())

def loop(q, model, steps, system, toolset, turns=8):
    use = dict(calls=0, in_tokens=0, out_tokens=0, cost=0.0, seconds=0.0)
    for _ in range(turns):
        last = max([i for i, s in enumerate(steps) if s["tool"] == "guard"], default=-1)
        n_tools = sum(1 for s in steps[last + 1:] if s["tool"] not in ("guard", "format"))
        r = call_llm(system, make_prompt(q["text"], steps, None, MAX_TOOLS - n_tools), model)
        for k in ("in_tokens", "out_tokens", "cost", "seconds"): use[k] += r[k]
        use["calls"] += 1
        act = parse_json(r["text"])
        if act is None or ("action" not in act and "can_answer" not in act):
            steps.append(dict(tool="format", args={}, result={"raw": r["text"][:200]})); continue
        if act.get("action") == "tool" and n_tools < MAX_TOOLS:
            args = act.get("args") if isinstance(act.get("args"), dict) else {}
            steps.append(dict(tool=act.get("tool"), args=args, result=run_tool(act.get("tool"), args, toolset=toolset))); continue
        return act, steps, use
    return None, steps, use

def run_item(job):
    kind, model, q = job["kind"], job["model"], job["q"]
    base = dict(kind=kind, model=model, qid=q["id"], set=q["set"])
    if kind == "D":
        r = call_llm(D_SYSTEM, f"Question: {q['text']}", model)
        return dict(base, final=parse_json(r["text"]), steps=[], calls=1, in_tokens=r["in_tokens"], out_tokens=r["out_tokens"], cost=r["cost"], seconds=r["seconds"], error=r.get("error"))
    if kind == "B2":
        final, steps, use = loop(q, model, [], agent_system(True), TOOLS)
        return dict(base, final=final, steps=steps, **use)
    final, steps, use = loop(q, model, [], E_SYSTEM, TOOLS2)
    rec = dict(base, final=final, steps=steps, **use)
    ok, msg = verify(final, steps)
    if not ok:
        steps2 = list(steps) + [dict(tool="guard", args={}, result={"message": msg})]
        final2, steps2, use2 = loop(q, model, steps2, E_SYSTEM, TOOLS2)
        rec["retry"] = dict(final=final2, steps=steps2[len(steps):], **use2, verifier_message=msg)
    return rec

if __name__ == "__main__":
    model = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    path = f"outputs/runs2_{model}.jsonl"
    done = {(json.loads(l)["kind"], json.loads(l)["qid"]) for l in open(path)} if os.path.exists(path) else set()
    jobs = [dict(kind="B2", model=model, q=q) for q in Q2] + [dict(kind=k, model=model, q=q) for k in ("E", "D") for q in Q1 + Q2]
    jobs = [j for j in jobs if (j["kind"], j["q"]["id"]) not in done]
    print(model, len(jobs), "items to run; D prompt chars:", len(D_SYSTEM), flush=True)
    call_llm(E_SYSTEM, "Reply OK", model); call_llm(D_SYSTEM, "Reply OK", model)     # warm the prompt cache
    with ThreadPoolExecutor(workers) as ex, open(path, "a") as f:
        for i, rec in enumerate(ex.map(run_item, jobs), 1):
            f.write(json.dumps(rec, default=str) + "\n"); f.flush()
            if i % 20 == 0: print(i, "done", flush=True)
