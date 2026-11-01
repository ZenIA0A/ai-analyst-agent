"""Study 2 question set: 24 harder questions (counting, largest changes, rankings of changes, long windows, multi-step arithmetic)
and 6 subtle traps. Built after study 1 hit a ceiling. Every expected answer is computed with plain pandas, not with the agent's tools."""
import json
import pandas as pd

D = "data/"
cash = pd.read_csv(D + "cash_rate_monthly.csv", index_col=0, parse_dates=True).cash_rate
rates = pd.read_csv(D + "rates_monthly.csv", index_col=0, parse_dates=True)
macro = pd.read_csv(D + "macro_quarterly.csv", index_col=0, parse_dates=True)
apra = pd.read_csv(D + "apra_panel_quarterly.csv", index_col=0, parse_dates=True)
G4 = ["Major banks", "Other domestic banks", "Foreign subsidiary banks", "Mutual ADIs"]
def ser(col, g="All ADIs"): return apra[apra.group == g][col]
def payment(rate_pct, loan=600000, n=360):
    r = rate_pct / 100 / 12; return loan * r / (1 - (1 + r) ** -n)

Q = []
def add(cat, text, truth, kind="number", tol=0.01):
    Q.append(dict(id=f"{cat}{sum(q['cat'] == cat for q in Q) + 1:02d}", cat=cat, text=text, type=kind, truth=truth, tol=tol))
def ordered(d, rev=True, gap=0.01):
    s = sorted(d.items(), key=lambda kv: kv[1], reverse=rev)
    assert all(abs(s[i][1] - s[i + 1][1]) > gap for i in range(len(s) - 1)), s
    return [k for k, _ in s]

dv = rates.disc_var_oo
add("X", "In how many months from January 2022 to September 2026 (inclusive) was the discounted variable owner-occupier rate at or above 6.0%?", int((dv["2022-01":"2026-09"] >= 6.0).sum()), tol=0)
o, a_ = ser("npl_ratio", "Other domestic banks"), ser("npl_ratio")
add("X", "In how many quarters from 2019Q1 to 2026Q2 was the non-performing loan ratio of Other domestic banks higher than that of all ADIs?", int((o > a_).sum()), tol=0)
d1 = a_.diff().dropna()
add("X", "In which quarter was the largest one-quarter increase in the all-ADIs non-performing loan ratio since 2019? Give the quarter-end date.", d1.idxmax().strftime("%Y-%m-%d"), "date")
add("X", "What was the largest one-quarter increase in the all-ADIs non-performing loan ratio since 2019, in percentage points?", float(d1.max()), tol=0.005)
add("X", "What was the largest one-month increase in the RBA cash rate target since January 2009, in percentage points?", float(cash.diff().max()), tol=0.001)
ch = {g: float(ser("npl_ratio", g)["2026-06-30"] - ser("npl_ratio", g)["2024-12-31"]) for g in G4}
add("X", "Rank the four lender groups (Major banks, Other domestic banks, Foreign subsidiary banks, Mutual ADIs) by the change in their non-performing loan ratio from 2024Q4 to 2026Q2, from the highest change (largest rise or smallest fall) to the lowest.", ordered(ch, gap=0.005), "list")
c = ser("credit_outstanding_m")
add("X", "By what percentage did housing credit outstanding for all ADIs grow from 2021Q4 to 2026Q2? Answer in %.", float((c["2026-06-30"] / c["2021-12-31"] - 1) * 100), tol=0.1)
hp = macro.house_price_index.dropna(); a0, a1 = "2019-12-31", hp.index[hp.index.year == 2025][-1]
yrs = (a1.year - 2019) + (a1.month - 12) / 12
add("X", f"What was the compound annual growth rate of the residential property price index from 2019Q4 to {a1.year}Q{(a1.month - 1) // 3 + 1}? Answer in % per year.", float(((hp[a1] / hp[a0]) ** (1 / yrs) - 1) * 100), tol=0.1)
add("X", "What was the average standard variable owner-occupier rate over the 60 months from January 2015 to December 2019? Answer in % per year.", float(rates.std_var_oo["2015-01":"2019-12"].mean()), tol=0.01)
gap = (rates.std_var_oo - rates.disc_var_oo)["2015-01":]
add("X", "What was the largest gap between the standard variable and the discounted variable owner-occupier rates in any month since January 2015, in percentage points?", float(gap.max()), tol=0.005)
m, mu = ser("npl_ratio", "Major banks"), ser("npl_ratio", "Mutual ADIs")
add("X", "By how many percentage points did the gap between the Major banks' and the Mutual ADIs' non-performing loan ratios (Major minus Mutual) change from 2022Q2 to 2026Q2?", float((m - mu)["2026-06-30"] - (m - mu)["2022-06-30"]), tol=0.01)
x = cash["2022-01":]; first = x[x >= 3.0].index[0]
add("X", "In which month after January 2022 did the RBA cash rate target first reach 3.0% or more? Give the month-end date.", first.strftime("%Y-%m-%d"), "date")
ib = macro.interest_burden["2019":].dropna()
add("X", "In how many quarters from 2019Q1 to 2026Q2 was the interest burden above 9.0% of household disposable income?", int((ib > 9.0).sum()), tol=0)
add("X", "What share of all ADIs' non-performing housing loans (in $) was held by the Major banks in 2026Q2? Answer in %.", float(ser("npl_m", "Major banks")["2026-06-30"] / ser("npl_m")["2026-06-30"] * 100), tol=0.2)
pdc = {g: float(ser("past_due_ratio", g)["2026-06-30"] - ser("past_due_ratio", g)["2025-06-30"]) for g in G4}
s_ = sorted(pdc.items(), key=lambda kv: kv[1]); assert s_[1][1] - s_[0][1] > 0.005
add("X", "Which of the four lender groups (excluding all ADIs) had the largest fall in its 30-89 days past-due ratio from 2025Q2 to 2026Q2?", s_[0][0], "string")
add("X", "What was the average non-performing loan ratio of Mutual ADIs over the four quarters of 2023? Answer in %.", float(mu["2023"].mean()), tol=0.005)
add("X", "How many times did the RBA change the cash rate target between January and September 2026 (month-end values)?", int((cash["2025-12":"2026-09"].diff().dropna() != 0).sum()), tol=0)
add("X", "How much higher was the monthly repayment on a $600,000, 30-year loan at the discounted variable owner-occupier rate of September 2026 than at the rate of September 2025? Answer in dollars.", float(payment(dv["2026-09-30"]) - payment(dv["2025-09-30"])), tol=2.0)
f3 = rates.fixed3y_oo
add("X", "By how many basis points did the 3-year fixed owner-occupier rate fall from its highest month in 2023 to its lowest month in 2025?", float((f3["2023"].max() - f3["2025"].min()) * 100), tol=1.0)
ex = ser("new_exceptions_share")["2023":]
add("X", "In how many quarters from 2023Q1 to 2026Q2 was the share of new lending approved as exceptions to policy (all ADIs) above 5%?", int((ex > 5).sum()), tol=0)
nl = ser("new_loans_m")
add("X", "What was the total value of new housing loans funded by all ADIs over the four quarters to 2026Q2? Answer in $ billion.", float(nl["2025-09-30":"2026-06-30"].sum() / 1000), tol=0.5)
add("X", "What was the ratio of the 30-89 days past-due ratio to the non-performing loan ratio for all ADIs in 2026Q2? Give a plain ratio (for example 0.5).", float(ser("past_due_ratio")["2026-06-30"] / a_["2026-06-30"]), tol=0.01)
mx = ser("npl_ratio", "Major banks")["2022":]
add("X", "What was the lowest non-performing loan ratio of the Major banks in any quarter since 2022, in %?", float(mx.min()), tol=0.005)
iu = macro.unemployment["2022":].dropna()
add("X", "By how many percentage points did Australia's unemployment rate rise from its lowest quarter since 2022 to 2026Q2?", float(iu["2026-06-30"] - iu.min()), tol=0.01)

# subtle traps: the tables cannot answer these
add("V", "What was the non-performing loan ratio on investor housing loans at Mutual ADIs in 2026Q2?", None, "abstain")
add("V", "What was the RBA cash rate target at the end of October 2026?", None, "abstain")
add("V", "What share of Foreign subsidiary banks' term loans had a loan-to-valuation ratio of 90% or more in 2026Q1?", None, "abstain")
add("V", "What was the non-performing housing loan ratio of the Commonwealth Bank in 2026Q2?", None, "abstain")
add("V", "What will Australia's unemployment rate be in 2027Q4?", None, "abstain")
add("V", "What was the average size of a new housing loan funded by all ADIs in 2026Q2, in dollars?", None, "abstain")

assert pd.isna(ser("lvr_ge90_share", "Foreign subsidiary banks")["2026-03-31"])
json.dump(Q, open("outputs/questions_hard.json", "w"), indent=1, default=str)
for q in Q: print(q["id"], q["truth"])
print(len(Q), "questions")
