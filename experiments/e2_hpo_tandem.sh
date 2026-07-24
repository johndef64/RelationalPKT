#!/usr/bin/env bash
# E2 (tandem) — run BOTH hyperparameter sweeps, Task A then Task B, with a reduced budget.
# Sequential by design: one GPU can't train two sweeps at once (they'd OOM / slow each other).
# Each e2_hpo_sweep.sh sweeps 2 models (rgcn + compgcn) x PKT_HPO_RUNS configs per task.
#
# Usage:   bash experiments/e2_hpo_tandem.sh                 # 40 runs/model (default)
#          PKT_HPO_RUNS=20 bash experiments/e2_hpo_tandem.sh # lighter
# Prereq:  wandb login   (entity/project hardcoded to RelationalPKT in tuning_hyperparameter.py)
set -euo pipefail
cd "$(dirname "$0")/.."

export PKT_HPO_RUNS="${PKT_HPO_RUNS:-40}"          # configs per model (x2 models x2 tasks)
# Early stopping is the main time lever. From the E1 log a good config converges by ~epoch
# 105 and would early-stop ~125; the tuning default (patience 50 evals) never triggers inside
# 200 epochs, so every trial wastes the full budget. patience=6 (=~35 epochs of no gain) stops
# plateaued trials ~epoch 125-140 -> ~35% faster, without cutting still-improving configs.
export PKT_HPO_PATIENCE="${PKT_HPO_PATIENCE:-6}"   # evaluations (every 5 epochs) w/o improvement
export PKT_HPO_EPOCHS="${PKT_HPO_EPOCHS:-200}"     # hard ceiling (rarely reached with the above)

echo "[E2-tandem] PKT_HPO_RUNS=$PKT_HPO_RUNS per model  ->  $((PKT_HPO_RUNS*2)) runs/task, $((PKT_HPO_RUNS*4)) total"
echo "[E2-tandem] === Task A (DTI) -> project RelationalPKT-DTI ==="
bash experiments/e2_hpo_sweep.sh A
echo "[E2-tandem] === Task B (TREATS) -> project RelationalPKT-TREATS ==="
bash experiments/e2_hpo_sweep.sh B

# Extract the best config per task straight from W&B (best-effort) and inject into
# src/models_params.json as PKT-DTI-best / PKT-TREATS-best.
echo "[E2-tandem] extracting best configs from W&B ..."
python experiments/get_best_hpo_config.py --task DTI    --write || echo "  (skip DTI: run get_best_hpo_config.py manually)"
python experiments/get_best_hpo_config.py --task TREATS --write || echo "  (skip TREATS: run get_best_hpo_config.py manually)"
echo "[E2-tandem] done. Best configs saved (experiments/hpo_best/) and injected as PKT-<TASK>-best."
echo "[E2-tandem] Final training:  HP_CONFIG=PKT-DTI-best bash experiments/e1_main_training.sh"
