#!/usr/bin/env bash
# Expert cohort review — wraps expert_review_script.py (repo root).
# Activates the `gnn` env via config.sh, so it runs WITHOUT activating conda first.
#
# 1) edit the config block at the top of expert_review_script.py
#    (TASK = A|B, MODEL_FOLDER, CANDIDATES = [] for all / or a pinned cohort)
# 2) build the review sheet:
#      bash experiments/expert_review.sh
# 3) after the expert fills expert_tier/expert_plausible/expert_notes, summarise:
#      bash experiments/expert_review.sh aggregate models/<folder>/drug_eval_results/<filled>.csv
set -euo pipefail
cd "$(dirname "$0")/.."
source experiments/config.sh
python expert_review_script.py "$@"
