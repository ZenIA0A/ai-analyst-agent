"""Scoring of final answers against the golden set, and the grounding guard (a control that checks an answer against tool results)."""
import json
import re
import pandas as pd
from tools import numbers_in, parse_date
import ast
from tools import _eval

def to_number(v):
    if isinstance(v, bool): return None
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = re.sub(r"[,$%\s]", "", v)
        try: return float(s)
        except ValueError: return None
    return None

def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

def score(q, final):
    """Return (correct, outcome). Outcomes: correct, wrong_value, false_abstain, false_answer, abstained_ok, format_error."""
    if not isinstance(final, dict) or "can_answer" not in final: return False, "format_error"
    can = final.get("can_answer") is True
    if q["type"] == "abstain": return (not can), ("abstained_ok" if not can else "false_answer")
    if not can: return False, "false_abstain"
    v = final.get("value")
    if q["type"] == "number":
        x = to_number(v)
        if x is None: return False, "format_error"
        return abs(x - q["truth"]) <= q["tol"], ("correct" if abs(x - q["truth"]) <= q["tol"] else "wrong_value")
    if q["type"] == "list":
        items = v if isinstance(v, list) else re.split(r",|;|>|\band\b", str(v)); ok = [norm(i) for i in items if norm(i)] == [norm(t) for t in q["truth"]]
    elif q["type"] == "string": ok = norm(v) == norm(q["truth"])
    else:
        try: ok = parse_date(v) == pd.Timestamp(q["truth"])
        except Exception: return False, "format_error"
    return ok, ("correct" if ok else "wrong_value")

def guard(final, steps):
    """Grounding guard. Returns (passed, message). A numeric answer must match a number returned by a tool (including the calculator);
    a text answer must appear in tool results. Answers that say 'cannot answer' always pass."""
    if not isinstance(final, dict) or final.get("can_answer") is not True: return True, ""
    results = [s["result"] for s in steps if isinstance(s.get("result"), dict) and "error" not in s["result"]]
    if not results: return False, "No tool result supports this answer. Use the tools or say can_answer false."
    v = final.get("value"); x = to_number(v)
    if x is not None:
        nums = [n for r in results for n in numbers_in(r) if isinstance(n, float)]
        if any(abs(x - n) <= max(0.006, 0.0005 * abs(x)) for n in nums): return True, ""
        return False, f"The value {v} does not match any number returned by the tools. Compute it with the calculate tool from tool results, or say can_answer false."
    text = json.dumps(results)
    if isinstance(v, list): return (all(str(i) in text for i in v)), "Every item in the list must appear in tool results."
    if str(v).lower() in ("yes", "no", "true", "false"): return True, ""         # yes/no answers rest on the tool results already checked
    return (str(v) in text), ("" if str(v) in text else f"'{v}' does not appear in any tool result.")


# ---------------- study 2: a verifier that checks the DERIVATION, not just where the final number appears
CONSTS = {0.0, 1.0, 2.0, 3.0, 4.0, 12.0, 100.0, 1000.0, 10000.0, 360.0, 600000.0, 0.5}
DATA_TOOLS = ("get_series", "summarise", "group_snapshot", "count_where", "max_change", "rank_groups")

def verify(final, steps):
    """Returns (passed, message). A numeric answer must come with a derivation: 'step N' (N = a data-tool result containing the value)
    or an arithmetic expression whose operands are numbers copied from data-tool results (plus a few unit constants), which must
    evaluate to the answer. Calculator results do not count as evidence, so '1+1+1' cannot ground a count."""
    if not isinstance(final, dict) or final.get("can_answer") is not True: return True, ""
    data = [s["result"] for s in steps if s.get("tool") in DATA_TOOLS and isinstance(s.get("result"), dict) and "error" not in s["result"]]
    if not data: return False, "No data-tool result supports this answer. Use the data tools or say can_answer false."
    nums = [n for r in data for n in numbers_in(r) if isinstance(n, float)]
    close = lambda a, b: abs(a - b) <= max(0.006, 0.0005 * abs(a))
    v = final.get("value"); x = to_number(v); der = str(final.get("derivation", "")).strip()
    if x is None:
        text = json.dumps(data)
        if isinstance(v, list): ok = all(str(i) in text for i in v)
        elif str(v).lower() in ("yes", "no", "true", "false"): ok = True
        else: ok = str(v) in text
        return ok, ("" if ok else f"'{v}' does not appear in any data-tool result.")
    m = re.fullmatch(r"step\s*(\d+)", der.lower())
    if m:
        i = int(m.group(1)) - 1
        if 0 <= i < len(steps) and steps[i].get("tool") in DATA_TOOLS and any(close(x, n) for n in numbers_in(steps[i]["result"]) if isinstance(n, float)): return True, ""
        return False, f"Step {i + 1} is not a data-tool result containing {v}. Give 'step N' for the data-tool result, or an arithmetic expression on numbers from data-tool results."
    if not der: return False, "Add a 'derivation' field: 'step N' or an arithmetic expression using numbers copied from data-tool results."
    try:
        tree = ast.parse(der.replace("^", "**"), mode="eval"); val = float(_eval(tree.body))
    except Exception:
        return False, "The derivation is not a valid arithmetic expression."
    lits = [float(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]
    from_data = [l for l in lits if any(close(l, n) for n in nums)]
    stray = [l for l in lits if l not in from_data and l not in CONSTS]
    if not from_data: return False, "The derivation uses no number from a data-tool result."
    if stray: return False, f"These numbers in the derivation do not come from data-tool results: {stray[:5]}."
    if not close(x, val) and not close(round(val, 2), x): return False, f"The derivation evaluates to {val:.6g}, not {v}."
    return True, ""
