#!/usr/bin/env bash
# Interpretability (standalone) — wraps experiments/interpret_predictions.py.
# Already run automatically inside e4_repurposing.sh; use this to run it on its own.
# Activates the `gnn` env via config.sh, so it runs WITHOUT activating conda first.
#
# Usage (pass the same args as interpret_predictions.py):
#   bash experiments/interpret.sh --rankings models/<folder>/drug_eval_results/*rankings*.json \
#        --tsv dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip --task_type A --topk 20
set -euo pipefail
cd "$(dirname "$0")/.."
source experiments/config.sh
python experiments/interpret_predictions.py "$@"
