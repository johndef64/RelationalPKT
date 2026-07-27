#!/usr/bin/env bash
# E3 — Ablation studies (adapted from PathogenKG). Two families:
#
#   E3a  COMPONENT ablation — turn off, one at a time, the imbalance-handling machinery
#        on the DTI task, to quantify each piece's contribution:
#          - focal loss off (alpha=1, gamma=0)          - adversarial off (alpha_adv=0)
#          - no oversampling (oversample_rate=1)        - no undersampling (undersample_rate=1.0)
#          - random negatives instead of filtered
#
#   E3b  RELATIONAL-CONTEXT ablation — train the DTI task on subgraphs that drop one context
#        layer at a time (built by analysis/07_build_ablation_subgraphs.py):
#          core_ppi / no_ppi / no_go / no_pathway / no_drugctx / full
#        This is the "topology-only, which context matters" ablation on PKT.
#
# Ablations use fewer seeds/epochs than E1 by default (override with RUNS/EPOCHS).
# Usage:  bash experiments/e3_ablation.sh            # both families
#         bash experiments/e3_ablation.sh component  # only E3a
#         bash experiments/e3_ablation.sh context    # only E3b
set -euo pipefail
cd "$(dirname "$0")/.."
source experiments/config.sh

WHICH="${1:-all}"
ABL_RUNS="${RUNS:-3}"; ABL_EPOCHS="${EPOCHS:-200}"
MODEL="${ABL_MODEL:-compgcn}"

train () {  # $1=tag  $2=tsv  ... extra flags
  local tag="$1" tsv="$2"; shift 2
  local log="${LOG_DIR}/e3_${tag}_$(date +%Y%m%d_%H%M%S).log"
  echo "[E3] $tag -> $log"
  local cfg; cfg="$(resolve_config "$TASK_A")"   # PKT-DTI-best if available, else $HP_CONFIG
  python train_and_eval.py --tsv "$tsv" --task "$TASK_A" --model "$MODEL" --config "$cfg" \
    --runs "$ABL_RUNS" --epochs "$ABL_EPOCHS" --early_stopping --patience "$PATIENCE" --eval_filtered "$@" \
    2>&1 | tee "$log"
}

component_ablation () {
  echo "== E3a component ablation (Task A / DTI) =="
  # full reference (all machinery on)
  train "comp_full"        "$TSV_A" --negative_sampling filtered --oversample_rate 5 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0
  # focal loss OFF (plain BCE-like: alpha=1, gamma=0)
  train "comp_no_focal"    "$TSV_A" --negative_sampling filtered --oversample_rate 5 --undersample_rate 0.5 --alpha 1.0 --gamma 0.0 --alpha_adv 2.0
  # adversarial negative weighting OFF
  train "comp_no_adv"      "$TSV_A" --negative_sampling filtered --oversample_rate 5 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 0.0
  # no oversampling of positives
  train "comp_no_oversmp"  "$TSV_A" --negative_sampling filtered --oversample_rate 1 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0
  # no undersampling of background
  train "comp_no_undersmp" "$TSV_A" --negative_sampling filtered --oversample_rate 5 --undersample_rate 1.0 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0
  # random negatives instead of filtered
  train "comp_rand_neg"    "$TSV_A" --negative_sampling standard --oversample_rate 5 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0
}

context_ablation () {
  echo "== E3b relational-context ablation (Task A / DTI) =="
  local abl="dataset/PKT_subgraphs/ablation"
  if [ ! -f "$abl/pkt_ablA_full.tsv.zip" ]; then
    echo "[E3b] building ablation subgraphs..."; python analysis/07_build_ablation_subgraphs.py
  fi
  for v in full core_ppi no_ppi no_go no_pathway no_drugctx; do
    train "ctx_${v}" "$abl/pkt_ablA_${v}.tsv.zip" \
      --oversample_rate 5 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0 --negative_sampling filtered
  done
}

case "$WHICH" in
  component) component_ablation ;;
  context)   context_ablation ;;
  all)       component_ablation; context_ablation ;;
  *) echo "usage: $0 [component|context|all]"; exit 1 ;;
esac
echo "[E3] done. Logs in ${LOG_DIR}/ ; compare final test metrics across tags."
