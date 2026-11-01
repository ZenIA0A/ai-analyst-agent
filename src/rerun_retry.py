"""Re-run guard retries that ran out of tool budget (harness bug found after the main run: a retry shared the 6-tool budget of the first attempt).
Only retries whose reply was an unexecuted tool call are re-run. The old retry is kept as retry_v1. Usage: python3 src/rerun_retry.py <model>"""
import json
import sys
sys.path.insert(0, "src")
from run_eval import agent_loop, agent_system
Q = {q["id"]: q for q in json.load(open("outputs/questions.json"))}
model = sys.argv[1]; path = f"outputs/runs_{model}.jsonl"
rows = [json.loads(l) for l in open(path)]
for r in rows:
    rt = r.get("retry")
    if r["kind"] == "agent" and rt and (rt["final"] or {}).get("action") == "tool" and "retry_v1" not in r:
        steps2 = list(r["steps"]) + [dict(tool="guard", args={}, result={"message": rt["guard_message"]})]
        final2, steps2, use2 = agent_loop(Q[r["qid"]], model, steps2, agent_system(defended=r.get("defended", True)), poisoned=False)
        r["retry_v1"] = rt
        r["retry"] = dict(final=final2, steps=steps2[len(r["steps"]):], **use2, guard_message=rt["guard_message"])
        print(model, r["qid"], "->", json.dumps(final2)[:200])
open(path, "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
