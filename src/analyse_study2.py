"""Analyse study 2: harder questions, better tools plus a derivation verifier (E), and tables-in-the-prompt without tools (D).
Writes outputs/study2_stats.json, outputs/study2_by_config.csv, outputs/study2_failures.csv and figure 7."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binomtest
from scoring import score, verify
import style as st
import ast
import re as _re
from tools import numbers_in, _eval
from scoring import to_number, DATA_TOOLS
from matplotlib.patches import Patch

st.setup()
Q = {q["id"]: dict(q, set="original") for q in json.load(open("outputs/questions.json"))}
Q.update({q["id"]: dict(q, set="hard") for q in json.load(open("outputs/questions_hard.json"))})
OVER = json.load(open("outputs/overhead2.json"))
MODELS = ["haiku", "sonnet"]; NAME = {"haiku": "Haiku 5.5", "sonnet": "Sonnet 5.5"}
CONF = {"B": "B. Agent, 4 tools (study 1 design)", "E": "E. Agent, 7 tools + derivation verifier", "D": "D. Tables in the prompt, no tools"}

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))

rows = []
for m in MODELS:
    o = OVER[m]
    net = lambda r: (max(r["cost"] - r["calls"] * o["cost"], 0), max(r["in_tokens"] - r["calls"] * o["in_tokens"], 0))
    for l in open(f"outputs/runs_{m}.jsonl"):            # study 1 agent (B) on the original 78
        r = json.loads(l)
        if r["kind"] != "agent": continue
        q = Q[r["qid"]]; ok, out = score(q, r["final"]); c_, t_ = net(r)
        rows.append(dict(model=m, config="B", set="original", qid=r["qid"], correct=ok, outcome=out, calls=r["calls"], cost=c_, in_tokens=t_, seconds=r["seconds"]))
    for l in open(f"outputs/runs2_{m}.jsonl"):
        r = json.loads(l); q = Q[r["qid"]]; c_, t_ = net(r)
        base = dict(model=m, set=q["set"], qid=r["qid"], calls=r["calls"], cost=c_, in_tokens=t_, seconds=r["seconds"])
        if r["kind"] in ("B2", "D"):
            ok, out = score(q, r["final"]); rows.append(dict(base, config="B" if r["kind"] == "B2" else "D", correct=ok, outcome=out)); continue
        ok1, out1 = score(q, r["final"]); passed, msg = verify(r["final"], r["steps"])
        if passed: fin, retry_ok = r["final"], None
        else:
            rt = r["retry"]; p2, _ = verify(rt["final"], r["steps"] + rt["steps"]); retry_ok = p2
            fin = rt["final"] if (rt["final"] is not None and p2) else {"can_answer": False, "value": None}
            c2, t2 = net(rt); base["calls"] += rt["calls"]; base["cost"] += c2; base["in_tokens"] += t2; base["seconds"] += rt["seconds"]
        ok, out = score(q, fin)
        rows.append(dict(base, config="E", correct=ok, outcome=out, first_correct=ok1, first_outcome=out1, blocked=not passed, retry_passed=retry_ok,
                         used_new_tool=any(s.get("tool") in ("count_where", "max_change", "rank_groups") for s in r["steps"] + (r.get("retry") or {}).get("steps", []))))
D = pd.DataFrame(rows)
D["bad"] = D.outcome.isin(["wrong_value", "false_answer"]); D["trap"] = D.qid.str[0].isin(["U", "V"])
S = {}

tab = []
for m in MODELS:
    for c in "BED":
        for s_ in ("original", "hard"):
            d = D[(D.model == m) & (D.config == c) & (D.set == s_)]
            if len(d) == 0: continue
            k, n = int(d.correct.sum()), len(d); lo, hi = wilson(k, n)
            tab.append(dict(model=m, config=c, set=s_, n=n, correct=k, accuracy=k / n, ci_lo=lo, ci_hi=hi, bad=int(d.bad.sum()),
                            false_abstain=int((d.outcome == "false_abstain").sum()), format_error=int((d.outcome == "format_error").sum()),
                            traps_refused=int(d[d.trap].correct.sum()), traps=int(d.trap.sum()), calls=d.calls.mean(), cost_per_100=d.cost.mean() * 100, seconds=d.seconds.mean()))
T = pd.DataFrame(tab); T.round(4).to_csv("outputs/study2_by_config.csv", index=False); S["table"] = T.round(4).to_dict("records")
print(T[["model", "config", "set", "n", "correct", "bad", "false_abstain", "format_error", "traps_refused", "calls", "cost_per_100"]].to_string(index=False))

def mcnemar(a, b):
    j = a.set_index("qid")[["correct"]].join(b.set_index("qid")[["correct"]], lsuffix="_a", rsuffix="_b", how="inner")
    x, y = int((j.correct_a & ~j.correct_b).sum()), int((~j.correct_a & j.correct_b).sum())
    return dict(only_a=x, only_b=y, n=len(j), p=round(float(binomtest(x, x + y, 0.5).pvalue), 3) if x + y else 1.0)
tests = {}
for m in MODELS:
    g = lambda c, s_: D[(D.model == m) & (D.config == c) & (D.set == s_)]
    tests[f"{m}: E vs B (hard)"] = mcnemar(g("E", "hard"), g("B", "hard"))
    tests[f"{m}: D vs B (hard)"] = mcnemar(g("D", "hard"), g("B", "hard"))
    tests[f"{m}: D vs B (original)"] = mcnemar(g("D", "original"), g("B", "original"))
    tests[f"{m}: E vs B (original)"] = mcnemar(g("E", "original"), g("B", "original"))
    tests[f"{m}: E vs D (hard)"] = mcnemar(g("E", "hard"), g("D", "hard"))
S["tests"] = tests; print(json.dumps(tests, indent=1))

# verifier effect in E
ve = {}
for m in MODELS:
    e = D[(D.model == m) & (D.config == "E")]
    ve[m] = dict(blocked=int(e.blocked.sum()), blocked_first_correct=int((e.blocked & e.first_correct).sum()), blocked_first_wrong=int((e.blocked & ~e.first_correct & e.first_outcome.isin(["wrong_value", "false_answer"])).sum()),
                 fixed_by_retry=int((e.blocked & ~e.first_correct & e.correct).sum()), lost_by_verifier=int((e.blocked & e.first_correct & ~e.correct).sum()),
                 bad_before=int(e.first_outcome.isin(["wrong_value", "false_answer"]).sum()), bad_after=int(e.bad.sum()), used_new_tool_hard=int(e[e.set == "hard"].used_new_tool.sum()))
S["verifier"] = ve; print(json.dumps(ve, indent=1))

# offline replay: a calibrated version of the verifier on E's FIRST answers (no new model calls, so no retries)
def verify_calibrated(final, steps):
    if not isinstance(final, dict) or final.get("can_answer") is not True: return True
    data = [s["result"] for s in steps if s.get("tool") in DATA_TOOLS and isinstance(s.get("result"), dict) and "error" not in s["result"]]
    if not data: return False
    nums = [n for r in data for n in numbers_in(r) if isinstance(n, float)]; text = json.dumps(data)
    close = lambda a, b: abs(a - b) <= max(0.006, 0.0005 * abs(a))
    fits = lambda l: any(close(abs(l), abs(n)) or close(l * 100, n) or close(l / 100, n) for n in nums)
    v = final.get("value"); x = to_number(v)
    if x is None:
        items = v if isinstance(v, list) else [i.strip() for i in _re.split(r",|;|>", str(v))]
        return all(str(i) in text for i in items if i)
    if fits(x): return True                                   # the value itself is in a data-tool result
    der = _re.split(r"=|\(step|where|,\s*where| from ", str(final.get("derivation", "")))[0].strip()
    try: tree = ast.parse(der.replace("^", "**"), mode="eval"); val = float(_eval(tree.body))
    except Exception: return False
    lits = [float(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]
    const = lambda l: (l == int(l) and abs(l) <= 12) or l in (100.0, 1200.0, 360.0, 600000.0, 1000.0, 10000.0)
    return any(fits(l) and not const(l) for l in lits) and all(fits(l) or const(l) for l in lits) and (close(x, val) or close(round(val, 2), x))
rep = {}
for m in MODELS:
    blk_ok = blk_bad = n_ = 0
    for l in open(f"outputs/runs2_{m}.jsonl"):
        r = json.loads(l)
        if r["kind"] != "E": continue
        q = Q[r["qid"]]; ok, out = score(q, r["final"]); n_ += 1
        if not verify_calibrated(r["final"], r["steps"]):
            blk_ok += ok; blk_bad += out in ("wrong_value", "false_answer")
    rep[m] = dict(n=n_, would_block_correct=int(blk_ok), would_block_bad=int(blk_bad))
S["calibrated_replay"] = rep; print("calibrated verifier replay", rep)

# failures, with the answer given
raw = {}
for m in MODELS:
    for l in open(f"outputs/runs2_{m}.jsonl"):
        r = json.loads(l); raw[(m, {"B2": "B"}.get(r["kind"], r["kind"]), r["qid"])] = r
F = []
for _, r in D[(~D.correct) & (D.set == "hard") | (~D.correct) & (D.config != "B")].iterrows():
    rr = raw.get((r.model, r.config, r.qid)); fin = (rr or {}).get("final") or {}
    F.append(dict(model=r.model, config=r.config, set=r.set, qid=r.qid, outcome=r.outcome, given=str(fin.get("value"))[:60], truth=str(Q[r.qid]["truth"])[:60], question=Q[r.qid]["text"][:110]))
F = pd.DataFrame(F).drop_duplicates(); F.to_csv("outputs/study2_failures.csv", index=False); print(F.to_string(index=False))
S["failures_by_qid"] = F[F.set == "hard"].groupby("qid").size().sort_values(ascending=False).to_dict()
json.dump(S, open("outputs/study2_stats.json", "w"), indent=1, default=float)

# figure 7: accuracy by configuration on each question set
fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
FILL = {"B": st.BLUE, "E": st.ORANGE, "D": st.TEAL}
for ax, s_, title in ((axs[0], "original", "Original 78 questions (study 1)"), (axs[1], "hard", "30 harder questions (study 2)")):
    for i, m in enumerate(MODELS):
        for j, c in enumerate("BED"):
            r = T[(T.model == m) & (T.config == c) & (T.set == s_)]
            if len(r) == 0: continue
            r = r.iloc[0]; x = i * 4 + j
            ax.bar(x, r.accuracy * 100, color=FILL[c], width=0.8)
            ax.errorbar(x, r.accuracy * 100, yerr=[[r.accuracy * 100 - r.ci_lo * 100], [r.ci_hi * 100 - r.accuracy * 100]], fmt="none", ecolor=st.INK2, capsize=3, lw=0.8)
            ax.text(x, 3, f"{r.accuracy*100:.0f}", ha="center", fontsize=8.5, color="white")
    ax.set_xticks([1, 5]); ax.set_xticklabels([NAME[m] for m in MODELS]); ax.set_title(title, loc="left", fontsize=10.5); ax.set_ylim(0, 105); st.clean(ax, "y")
axs[0].set_ylabel("Correct answers, % (95% interval)")
fig.legend(handles=[Patch(facecolor=FILL[c], label=CONF[c]) for c in "BED"], frameon=False, fontsize=8.5, ncol=3, loc="lower center")
fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig("outputs/fig7_study2.png", dpi=200); plt.close(fig)
print("saved")
