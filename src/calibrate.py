"""Measure the fixed overhead of one Claude Code print-mode call (a trivial prompt, warm cache), so tokens and cost of the study can be reported net of it."""
import json
import statistics
from llm import call_llm

out = {}
for m in ["haiku", "sonnet"]:
    call_llm("You are a test.", "Reply with exactly: OK", m)          # warm the cache
    rs = [call_llm("You are a test.", "Reply with exactly: OK", m) for _ in range(5)]
    out[m] = dict(in_tokens=statistics.median(r["in_tokens"] for r in rs), cost=statistics.median(r["cost"] for r in rs), seconds=statistics.median(r["seconds"] for r in rs))
json.dump(out, open("outputs/overhead.json", "w"), indent=1); print(out)
