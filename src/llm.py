"""One function to call a language model. Two backends:
  - 'cli': Claude Code print mode (used for the runs in this repo; no API key needed inside the build sandbox)
  - 'api': Anthropic Messages API (set ANTHROPIC_API_KEY; pip install anthropic) for anyone re-running the study
Both return text plus token counts, cost and latency so the cost-quality trade-off can be measured."""
import json
import os
import subprocess
import tempfile
import time

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
BACKEND = os.environ.get("LLM_BACKEND", "cli")

def call_cli(system, prompt, model, timeout=150):
    cmd = ["claude", "-p", prompt, "--model", model, "--tools", "", "--system-prompt", system, "--output-format", "json",
           "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands"]
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tempfile.gettempdir())
    d = json.loads(out.stdout)
    u = d["usage"]
    return dict(text=d["result"], in_tokens=u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"],
                out_tokens=u["output_tokens"], cost=d["total_cost_usd"], seconds=time.time() - t0)

def call_api(system, prompt, model, timeout=150):
    import anthropic
    t0 = time.time()
    r = anthropic.Anthropic().messages.create(model=MODELS[model], max_tokens=800, system=system, messages=[{"role": "user", "content": prompt}], timeout=timeout)
    return dict(text=r.content[0].text, in_tokens=r.usage.input_tokens, out_tokens=r.usage.output_tokens, cost=0.0, seconds=time.time() - t0)

def call_llm(system, prompt, model, tries=3):
    last = None
    for i in range(tries):
        try:
            return (call_cli if BACKEND == "cli" else call_api)(system, prompt, model)
        except Exception as e:               # network or parse hiccup: wait and try again
            last = e; time.sleep(2 + 3 * i)
    return dict(text="", in_tokens=0, out_tokens=0, cost=0.0, seconds=0.0, error=str(last)[:200])
