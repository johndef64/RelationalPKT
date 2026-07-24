#!/usr/bin/env bash
# Shared configuration for all PKT experiments. Sourced by the e*.sh scripts.
# Edit here once; every experiment picks it up.

# ---- conda env ----
export CONDA_ENV="${CONDA_ENV:-gnn}"

# ---- datasets (built by analysis/06_build_subgraphs.py) ----
export TSV_A="dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip"      # Task A: predict DTI
export TSV_B="dataset/PKT_subgraphs/pkt_taskB_treats.tsv.zip"   # Task B: predict TREATS

# ---- task target relation names (interaction column) ----
export TASK_A="DTI"
export TASK_B="TREATS"

# ---- compound-centric target node type (drug_eval --target_type) ----
export TGT_A="Protein"
export TGT_B="Disease"

# ---- model / hyperparameter config (key in src/models_params.json) ----
# BIOKG-128 = DRKG-scale biomedical config (right scale for PKT ~66-94k nodes).
export HP_CONFIG="${HP_CONFIG:-BIOKG-128}"
export MODELS="${MODELS:-compgcn rgcn}"    # primary + baseline

# ---- training budget (PathogenKG Table-4 protocol) ----
export RUNS="${RUNS:-12}"
export EPOCHS="${EPOCHS:-400}"
export PATIENCE="${PATIENCE:-20}"

# ---- common training flags (focal loss + adversarial + filtered, PathogenKG defaults) ----
export COMMON_FLAGS="--early_stopping --patience ${PATIENCE} --negative_sampling filtered --eval_filtered \
--oversample_rate 5 --undersample_rate 0.5 --alpha 0.25 --gamma 3.0 --alpha_adv 2.0"

# ---- logging ----
export LOG_DIR="${LOG_DIR:-experiments/logs}"
mkdir -p "$LOG_DIR"

# Activate conda env if available (harmless if already active)
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
  conda activate "$CONDA_ENV" 2>/dev/null || true
fi

echo "[config] env=$CONDA_ENV config=$HP_CONFIG runs=$RUNS epochs=$EPOCHS models='$MODELS'"
