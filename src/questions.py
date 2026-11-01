"""Build the golden question set. Every expected answer is computed from the data with plain pandas (not with the agent's tools)."""
import json
import pandas as pd

D = "data/"
cash = pd.read_csv(D + "cash_rate_monthly.csv", index_col=0, parse_dates=True)
rates = pd.read_csv(D + "rates_monthly.csv", index_col=0, parse_dates=True)
macro = pd.read_csv(D + "macro_quarterly.csv", index_col=0, parse_dates=True)
apra = pd.read_csv(D + "apra_panel_quarterly.csv", index_col=0, parse_dates=True)
T = pd.Timestamp

def ap(col, date, group="All ADIs"):
    return float(apra[(apra.group == group) & (apra.index == T(date))][col].iloc[0])
def payment(rate_pct, loan=600000, n=360):
    r = rate_pct / 100 / 12
    return loan * r / (1 - (1 + r) ** -n)
GROUPS4 = ["Major banks", "Other domestic banks", "Foreign subsidiary banks", "Mutual ADIs"]
def best(col, date, how="max"):
    v = {g: ap(col, date, g) for g in GROUPS4}
    s = sorted(v.items(), key=lambda kv: kv[1], reverse=(how == "max")); assert abs(s[0][1] - s[1][1]) > 0.03, (col, date, s)
    return s[0][0]

Q = []
def add(cat, text, truth, kind="number", tol=0.01):
    Q.append(dict(id=f"{cat}{sum(q['cat'] == cat for q in Q) + 1:02d}", cat=cat, text=text, type=kind, truth=truth, tol=tol))

# L = lookup
add("L", "What was the RBA cash rate target at the end of December 2023? Answer in % per year.", float(cash.cash_rate["2023-12-31"]), tol=0.001)
add("L", "What was the discounted variable owner-occupier mortgage rate at the end of September 2025? Answer in % per year.", float(rates.disc_var_oo["2025-09-30"]), tol=0.005)
add("L", "What was the interest burden (interest payments on housing debt as % of household disposable income) in 2026Q2? Answer in %.", float(macro.interest_burden["2026-06-30"]))
add("L", "What was Australia's unemployment rate in 2026Q2? Answer in %.", float(macro.unemployment["2026-06-30"]))
add("L", "What was the non-performing housing loan ratio for all ADIs in 2026Q2? Answer in %.", ap("npl_ratio", "2026-06-30"))
add("L", "What share of housing loans were 30 to 89 days past due at the major banks in 2026Q2? Answer in %.", ap("past_due_ratio", "2026-06-30", "Major banks"))
add("L", "What was housing credit outstanding for all ADIs in 2026Q2? Answer in $ billion.", ap("credit_outstanding_m", "2026-06-30") / 1000, tol=1.0)
add("L", "What share of Mutual ADIs' housing credit was investor lending in 2026Q2? Answer in %.", ap("investor_share", "2026-06-30", "Mutual ADIs"), tol=0.05)
add("L", "What was housing debt as % of annual household disposable income in 2022Q4?", float(macro.housing_debt_to_income["2022-12-31"]), tol=0.05)
add("L", "What was the standard variable owner-occupier mortgage rate at the end of December 2024? Answer in % per year.", float(rates.std_var_oo["2024-12-31"]), tol=0.005)

# C = change over a period
add("C", "By how many percentage points did the RBA cash rate target change between the end of December 2021 and the end of December 2023?", float(cash.cash_rate["2023-12-31"] - cash.cash_rate["2021-12-31"]))
add("C", "By how many percentage points did the discounted variable owner-occupier rate change between the end of December 2021 and the end of December 2023?", float(rates.disc_var_oo["2023-12-31"] - rates.disc_var_oo["2021-12-31"]))
add("C", "By how many percentage points did the interest burden change between 2021Q3 and 2023Q4?", float(macro.interest_burden["2023-12-31"] - macro.interest_burden["2021-09-30"]))
add("C", "By how many percentage points did the all-ADI non-performing housing loan ratio change between 2022Q4 and 2025Q1?", ap("npl_ratio", "2025-03-31") - ap("npl_ratio", "2022-12-31"))
add("C", "By how many percentage points did housing debt to income change between 2019Q2 and 2026Q2?", float(macro.housing_debt_to_income["2026-06-30"] - macro.housing_debt_to_income["2019-06-30"]), tol=0.05)
add("C", "By how many percentage points did the RBA cash rate target change between the end of August 2025 and the end of September 2026?", float(cash.cash_rate["2026-09-30"] - cash.cash_rate["2025-08-31"]))
add("C", "By what percentage did all-ADI housing credit outstanding grow between 2023Q2 and 2026Q2? Answer in %.", (ap("credit_outstanding_m", "2026-06-30") / ap("credit_outstanding_m", "2023-06-30") - 1) * 100, tol=0.1)
add("C", "By how many percentage points did the share of loans 30 to 89 days past due at the major banks change between 2025Q4 and 2026Q2?", ap("past_due_ratio", "2026-06-30", "Major banks") - ap("past_due_ratio", "2025-12-31", "Major banks"))

# E = extremes and timing
bm = macro.interest_burden
add("E", "In which quarter was the interest burden highest in the data? Answer with the quarter-end date as YYYY-MM-DD.", bm.idxmax().strftime("%Y-%m-%d"), "date")
add("E", "What was the highest interest burden in the data? Answer in %.", float(bm.max()))
n22 = apra[(apra.group == "All ADIs") & (apra.index >= "2022-01-01")].npl_ratio
add("E", "Since 2022, in which quarter was the all-ADI non-performing housing loan ratio lowest? Answer with the quarter-end date as YYYY-MM-DD.", n22.idxmin().strftime("%Y-%m-%d"), "date")
add("E", "What was the lowest all-ADI non-performing housing loan ratio since 2022? Answer in %.", float(n22.min()))
add("E", "What was the highest monthly RBA cash rate target between January 2022 and September 2026? Answer in %.", float(cash.cash_rate["2022-01-31":"2026-09-30"].max()), tol=0.001)
n24 = apra[(apra.group == "All ADIs") & (apra.index >= "2024-01-01")].npl_ratio
assert n24.nlargest(2).iloc[0] - n24.nlargest(2).iloc[1] > 0.004
add("E", "Since 2024, in which quarter was the all-ADI non-performing housing loan ratio highest? Answer with the quarter-end date as YYYY-MM-DD.", n24.idxmax().strftime("%Y-%m-%d"), "date")
add("E", "What was the lowest interest burden since the start of 2022? Answer in %.", float(bm["2022-01-01":].min()))
add("E", "What was the highest unemployment rate in the data from 2022 to 2026Q2? Answer in %.", float(macro.unemployment["2022-01-01":].max()))

# G = comparing lender groups
add("G", "Among the four lender groups (major banks, other domestic banks, foreign subsidiary banks, mutual ADIs), which had the lowest non-performing housing loan ratio in 2026Q2?", best("npl_ratio", "2026-06-30", "min"), "string")
add("G", "Among the four lender groups, which had the highest non-performing housing loan ratio in 2025Q1?", best("npl_ratio", "2025-03-31", "max"), "string")
add("G", "Among the four lender groups, which had the highest investor share of housing credit in 2026Q2?", best("investor_share", "2026-06-30"), "string")
add("G", "Among the four lender groups, which had the highest share of interest-only loans in 2026Q2?", best("io_share", "2026-06-30"), "string")
add("G", "How many percentage points higher was the major banks' non-performing ratio than the mutual ADIs' in 2026Q2?", ap("npl_ratio", "2026-06-30", "Major banks") - ap("npl_ratio", "2026-06-30", "Mutual ADIs"))
add("G", "Among the four lender groups, which had the largest housing credit outstanding in 2026Q2?", best("credit_outstanding_m", "2026-06-30"), "string")
add("G", "What share of all-ADI housing credit was held by the major banks in 2026Q2? Answer in %.", ap("credit_outstanding_m", "2026-06-30", "Major banks") / ap("credit_outstanding_m", "2026-06-30") * 100, tol=0.1)
add("G", "Among the four lender groups, which had the highest share of loans 30 to 89 days past due in 2026Q2?", best("past_due_ratio", "2026-06-30"), "string")

# D = derived, several steps
add("D", "Using macro_quarterly, compute housing debt to income x discounted variable rate / 100 for 2026Q2. Answer in %.", float(macro.housing_debt_to_income["2026-06-30"] * macro.disc_var_oo["2026-06-30"] / 100))
add("D", "What is the monthly repayment on a $600,000, 30-year (360 months) principal-and-interest loan at the discounted variable owner-occupier rate at the end of September 2025? Use monthly compounding. Answer in dollars.", payment(float(rates.disc_var_oo["2025-09-30"])), tol=2.0)
add("D", "What is the monthly repayment on a $600,000, 30-year (360 months) principal-and-interest loan at the discounted variable owner-occupier rate at the end of December 2021? Use monthly compounding. Answer in dollars.", payment(float(rates.disc_var_oo["2021-12-31"])), tol=2.0)
add("D", "What was the spread between the discounted variable owner-occupier rate and the cash rate at the end of June 2026, in percentage points?", float(rates.disc_var_oo["2026-06-30"] - rates.cash_rate["2026-06-30"]))
add("D", "How many times larger was the major banks' non-performing ratio than the mutual ADIs' in 2026Q2?", ap("npl_ratio", "2026-06-30", "Major banks") / ap("npl_ratio", "2026-06-30", "Mutual ADIs"), tol=0.02)
add("D", "How many times larger was the all-ADI stock of non-performing housing loans (in $ million) in 2026Q2 than in 2022Q4?", ap("npl_m", "2026-06-30") / ap("npl_m", "2022-12-31"), tol=0.02)
add("D", "What was the average discounted variable owner-occupier rate over the 12 months of calendar 2025? Answer in % per year.", float(rates.disc_var_oo["2025-01-01":"2025-12-31"].mean()))
add("D", "By how many dollars did annual interest on a $600,000 loan at the discounted variable owner-occupier rate rise between the end of December 2021 and the end of December 2023? (annual interest = balance x rate)", 600000 * float(rates.disc_var_oo["2023-12-31"] - rates.disc_var_oo["2021-12-31"]) / 100, tol=50)


# H = harder multi-step questions (counting, date arithmetic, ranking, cross-checks). Counting needs the model to read many rows.
def qshift(date, n): return (T(date) + pd.offsets.QuarterEnd(n)).normalize()
peak = bm.idxmax(); a_all = apra[apra.group == "All ADIs"]
add("H", "Find the quarter with the highest interest burden. What was the all-ADI non-performing housing loan ratio exactly five quarters after that quarter? Answer in %.", ap("npl_ratio", qshift(peak, 5).strftime("%Y-%m-%d")))
c = a_all.npl_ratio["2022-01-01":"2026-06-30"]; assert (abs(c - 1.0) > 0.003).all()
add("H", "From 2022Q1 to 2026Q2 inclusive, in how many quarters was the all-ADI non-performing housing loan ratio above 1.0%? Answer with a whole number.", int((c > 1.0).sum()), tol=0)
c = rates.disc_var_oo["2022-01-01":"2026-09-30"]; assert (abs(c - 6.5) > 0.005).all()
add("H", "Between January 2022 and September 2026 inclusive, in how many months was the discounted variable owner-occupier rate above 6.5%? Answer with a whole number.", int((c > 6.5).sum()), tol=0)
c = a_all.past_due_ratio; thr = next(t for t in (0.6, 0.55, 0.65, 0.5, 0.7) if (abs(c - t) > 0.003).all())
add("H", f"Across all quarters in the APRA data, in how many quarters was the all-ADI share of loans 30 to 89 days past due above {thr}%? Answer with a whole number.", int((c > thr).sum()), tol=0)
def ranking(col, date):
    v = {g: ap(col, date, g) for g in GROUPS4}; s = sorted(v.items(), key=lambda kv: -kv[1]); gaps = [s[i][1] - s[i + 1][1] for i in range(3)]; return s, min(gaps)
rd = next(d for d in ["2025-03-31", "2024-12-31", "2024-09-30", "2025-06-30", "2025-09-30", "2024-06-30"] if ranking("npl_ratio", d)[1] > 0.03)
add("H", f"Rank the four lender groups from the highest to the lowest non-performing housing loan ratio in {rd[:4]}Q{(int(rd[5:7]) - 1) // 3 + 1}. Give the four group names in order, separated by commas.", [g for g, _ in ranking("npl_ratio", rd)[0]], "list")
inc = {g: ap("npl_ratio", "2025-03-31", g) - ap("npl_ratio", "2022-12-31", g) for g in GROUPS4}; s = sorted(inc.items(), key=lambda kv: -kv[1]); assert s[0][1] - s[1][1] > 0.03
add("H", "Which of the four lender groups had the largest increase in its non-performing housing loan ratio between 2022Q4 and 2025Q1?", s[0][0], "string")
ok = abs(macro.interest_burden_std["2026-06-30"] - macro.housing_debt_to_income["2026-06-30"] * macro.std_var_oo["2026-06-30"] / 100) < 0.005
add("H", "In macro_quarterly for 2026Q2, does interest_burden_std equal housing debt to income x standard variable owner-occupier rate / 100, to within 0.005? Answer yes or no.", "yes" if ok else "no", "string")
add("H", "What was the average of the house price index at the four quarter-ends of 2025?", float(macro.house_price_index["2025-01-01":"2025-12-31"].mean()), tol=0.05)
add("H", "What was the compound annual growth rate of all-ADI housing credit between 2023Q2 and 2026Q2 (three years)? Answer in % per year.", ((ap("credit_outstanding_m", "2026-06-30") / ap("credit_outstanding_m", "2023-06-30")) ** (1 / 3) - 1) * 100, tol=0.05)
add("H", "A new $600,000, 30-year (360 months) principal-and-interest loan is written at the discounted variable owner-occupier rate. By how many dollars is the monthly repayment higher at the end-December 2023 rate than at the end-December 2021 rate? Use monthly compounding.", payment(float(rates.disc_var_oo["2023-12-31"])) - payment(float(rates.disc_var_oo["2021-12-31"])), tol=3)
lo_q = n22.idxmin().strftime("%Y-%m-%d")
add("H", "Find the quarter since 2022 in which the all-ADI non-performing housing loan ratio was lowest. In that quarter, which of the four lender groups had the highest non-performing ratio?", best("npl_ratio", lo_q), "string")
add("H", "Find the quarter with the highest interest burden. What was the RBA cash rate target (monthly table) at the end of the month 18 months before that quarter-end? Answer in %.", float(cash.cash_rate[(peak - pd.DateOffset(months=18) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")]), tol=0.001)
add("H", "Since January 2019, what was the largest gap between the discounted variable owner-occupier rate and the RBA cash rate target, in percentage points (rates_monthly)?", float((rates.disc_var_oo - rates.cash_rate)["2019-01-01":].max()))
add("H", "In 2026Q2, what was the all-ADI share of loans 30 to 89 days past due divided by the non-performing ratio?", ap("past_due_ratio", "2026-06-30") / ap("npl_ratio", "2026-06-30"), tol=0.01)
add("H", "At the end of June 2026, by what percentage was the standard variable owner-occupier rate higher than the discounted variable rate? Answer in %.", (float(rates.std_var_oo["2026-06-30"]) / float(rates.disc_var_oo["2026-06-30"]) - 1) * 100, tol=0.05)
add("H", "How many times larger was the major banks' housing credit outstanding than the other domestic banks' in 2026Q2?", ap("credit_outstanding_m", "2026-06-30", "Major banks") / ap("credit_outstanding_m", "2026-06-30", "Other domestic banks"), tol=0.02)
add("H", "Since 2019Q2, what was the largest one-quarter fall in the interest burden, in percentage points? Give it as a positive number.", float(-bm["2019-01-01":].diff().min()), tol=0.01)
add("H", "Since January 2022, in which month did the RBA cash rate target first reach 4.00% or more? Answer with the month-end date as YYYY-MM-DD.", cash.cash_rate["2022-01-01":][cash.cash_rate["2022-01-01":] >= 4.0].index[0].strftime("%Y-%m-%d"), "date")
add("H", "Before September 2026, what was the last month-end at which the RBA cash rate target was below 4.00%? Answer as YYYY-MM-DD.", cash.cash_rate["2026-01-01":"2026-08-31"][cash.cash_rate["2026-01-01":"2026-08-31"] < 4.0].index[-1].strftime("%Y-%m-%d"), "date")
add("H", "How many of the four lender groups had a higher non-performing housing loan ratio in 2026Q2 than in 2025Q1? Answer with a whole number.", sum(ap("npl_ratio", "2026-06-30", g) > ap("npl_ratio", "2025-03-31", g) for g in GROUPS4), tol=0)

# U = cannot be answered from these tables (the right answer is to say so)
U = ["What will the RBA cash rate target be at the end of December 2027?",
     "What was the all-ADI non-performing housing loan ratio in 2026Q4?",
     "What was the non-performing housing loan ratio at Westpac in 2026Q2?",
     "What share of housing loans in arrears are in Western Australia?",
     "Why did APRA raise the cash rate in 2024, and by how much?",
     "What share of the major banks' housing loans had a loan-to-valuation ratio of 90% or more in 2026Q2?",
     "What was Australia's unemployment rate in 2026Q3?",
     "What was the residential property price index in 2026Q2?",
     "What share of new housing loans funded in 2026Q2 were fixed-rate?",
     "What was the 5-year fixed owner-occupier mortgage rate at the end of June 2023?",
     "What was the unemployment rate for women aged 15 to 24 in 2026Q2?",
     "What will the all-ADI non-performing housing loan ratio be at the end of 2028 if the cash rate rises to 5.10%?"]
U += ["What was the all-ADI non-performing ratio for investor loans in 2026Q2?",
      "What was the RBA cash rate target at the end of October 2026?",
      "What was the major banks' non-performing housing loan ratio in 2018Q4?",
      "Which lender group had the highest non-performing housing loan ratio in 2026Q3?"]
for t in U: add("U", t, None, "abstain")

# checks that the unanswerable ones really are missing in the data
assert pd.isna(macro.house_price_index["2026-06-30"]) and "2026-09-30" not in macro.index.strftime("%Y-%m-%d")
assert pd.isna(apra[(apra.group == "Major banks") & (apra.index == "2026-06-30")].lvr_ge90_share.iloc[0])
assert apra.index.max() == T("2026-06-30")
json.dump(Q, open("outputs/questions.json", "w"), indent=1)
print(len(Q), "questions;", {c: sum(q["cat"] == c for q in Q) for c in "LCEGDHU"})
for q in Q: print(q["id"], q["truth"] if not isinstance(q["truth"], float) else round(q["truth"], 4))
