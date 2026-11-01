#!/usr/bin/env bash
# Reproduce the study. Run from the project folder: bash run_all.sh
# Steps 2 and 3 call models. They need the `claude` CLI (default backend) or ANTHROPIC_API_KEY (see src/llm.py).
# They are resumable and skip finished items. outputs/runs_*.jsonl already holds the logged runs, so you can set SKIP_MODELS=1
# to rebuild the analysis, figures and report without any model calls.
set -e
cd "$(dirname "$0")"
mkdir -p outputs docs
python3 src/questions.py                       # 78 questions with independently computed answers -> outputs/questions.json
python3 src/questions_hard.py                  # study 2: 30 harder questions -> outputs/questions_hard.json
if [ -z "$SKIP_MODELS" ]; then
  python3 src/run_eval.py haiku 4               # closed book (A1, A2), agent (B, with guard retry) and injection runs
  python3 src/run_eval.py sonnet 4
  python3 src/rerun_retry.py haiku              # re-run retries that ran out of tool budget (see report, section 6)
  python3 src/rerun_retry.py sonnet
  python3 src/calibrate.py                      # fixed per-call overhead of the CLI backend -> outputs/overhead.json
  python3 src/run_study2.py haiku 4             # study 2: tool agent (B), tools + verifier (E), tables in prompt (D)
  python3 src/run_study2.py sonnet 4
fi
python3 src/analyse.py                          # tables, statistics, figures 1 to 6
python3 src/analyse_study2.py                   # study 2 tables, tests, verifier replay, figure 7
python3 src/diagram.py                          # architecture figure
python3 src/05_build_report.py                  # docs/AI_analyst_agent_report.docx
