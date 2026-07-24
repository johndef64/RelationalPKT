#!/usr/bin/env bash
# Resume an interrupted HPO sweep — re-attaches an agent to the SAVED sweep id
# (experiments/hpo_sweeps/<project>.txt) instead of starting a new sweep. The Bayesian
# search continues, reusing the trials already logged on W&B.
#
# Note: this runs PKT_HPO_RUNS MORE trials on the existing sweep (there is no "finish to N
# total" in W&B). Lower it to add fewer, e.g. PKT_HPO_RUNS=15.
#
# Usage:  bash experiments/resume_hpo.sh A        # resume Task A sweeps (rgcn + compgcn)
#         PKT_HPO_RUNS=15 bash experiments/resume_hpo.sh B
set -euo pipefail
cd "$(dirname "$0")/.."
WHICH="${1:-A}"
export PKT_HPO_RESUME=1
echo "[resume] re-attaching agents to saved sweep(s) for task $WHICH (PKT_HPO_RUNS=${PKT_HPO_RUNS:-100})"
bash experiments/e2_hpo_sweep.sh "$WHICH"
