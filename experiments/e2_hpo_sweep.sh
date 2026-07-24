#!/usr/bin/env bash
# E2 — Hyperparameter optimisation  (PathogenKG §3.2/§3.3 — Bayesian W&B sweep).
# Optimises the composite metric M = 0.2*AUROC + 0.4*AUPRC + 0.4*MRR on the validation set.
# Runs one sweep per task; models swept = AVAILABLE_MODELS in tuning_hyperparameter.py
# (rgcn + compgcn). Best configs then go into src/models_params.json for the final E1 runs.
#
# PREREQUISITES:
#   pip install wandb && wandb login
#   (W&B entity/project are hardcoded in tuning_hyperparameter.py = RelationalPKT;
#    override here with WANDB_ENTITY / WANDB_PROJECT env vars if needed.)
#
# Usage:   bash experiments/e2_hpo_sweep.sh A     # sweep Task A (project RelationalPKT-DTI)
#          bash experiments/e2_hpo_sweep.sh B     # sweep Task B (project RelationalPKT-TREATS)
set -euo pipefail
cd "$(dirname "$0")/.."
source experiments/config.sh

WHICH="${1:-A}"

if [ "$WHICH" = "A" ]; then
  export PKT_TSV="$TSV_A"; export PKT_TASK="$TASK_A"; export WANDB_PROJECT="RelationalPKT-DTI"
else
  export PKT_TSV="$TSV_B"; export PKT_TASK="$TASK_B"; export WANDB_PROJECT="RelationalPKT-TREATS"
fi
export PKT_HPO_EPOCHS="${PKT_HPO_EPOCHS:-200}"
export PKT_HPO_PATIENCE="${PKT_HPO_PATIENCE:-50}"
export PKT_HPO_RUNS="${PKT_HPO_RUNS:-100}"

log="${LOG_DIR}/e2_hpo_${WHICH}_$(date +%Y%m%d_%H%M%S).log"
echo "[E2] sweep task=$WHICH tsv=$PKT_TSV project=$WANDB_PROJECT runs=$PKT_HPO_RUNS -> $log"
python tuning_hyperparameter.py 2>&1 | tee "$log"
echo "[E2] done. Inspect the sweep on W&B; copy the best config into src/models_params.json."
