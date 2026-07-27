#!/usr/bin/env bash
# E1 — Main training & model comparison  (PathogenKG §3.1 / Table 4, adapted to PKT).
# For each task (A=DTI, B=TREATS) x each model (compgcn, rgcn): RUNS seeds, EPOCHS epochs,
# filtered evaluation. Produces per-run + aggregated AUROC/AUPRC/MRR/Hits@k and saves the
# trained model under models/<task>_<dataset>_<timestamp>/.
#
# Usage:   bash experiments/e1_main_training.sh
#          RUNS=12 EPOCHS=400 MODELS="compgcn rgcn" bash experiments/e1_main_training.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source experiments/config.sh

run_one () {  # $1=tsv  $2=task  $3=model
  local tsv="$1" task="$2" model="$3"
  local cfg; cfg="$(resolve_config "$task")"   # PKT-<task>-best if available, else $HP_CONFIG
  local log="${LOG_DIR}/e1_${task}_${model}_$(date +%Y%m%d_%H%M%S).log"
  echo "[E1] task=$task model=$model config=$cfg -> $log"
  python train_and_eval.py \
    --tsv "$tsv" --task "$task" --model "$model" --config "$cfg" \
    --runs "$RUNS" --epochs "$EPOCHS" $COMMON_FLAGS 2>&1 | tee "$log"
}

for m in $MODELS; do run_one "$TSV_A" "$TASK_A" "$m"; done   # Task A (DTI)
for m in $MODELS; do run_one "$TSV_B" "$TASK_B" "$m"; done   # Task B (TREATS)

echo "[E1] done. Trained models are in models/ ; logs in ${LOG_DIR}/"
