import os
import sys
import glob
import json
import time
import subprocess
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))
from interpret_predictions import load_subgraph, annotate   # KG-evidence interpretability

"""
expert_review_script.py — PathogenKG-style biological review driver, adapted to PKT.

Runs the compound-centric ranking (drug_eval.py) for a cohort of drugs with the mature model,
attaches the KG-evidence interpretability (interpret_predictions), joins human-readable node
labels, and writes a REVIEW SHEET with empty columns for an expert to fill in the 3 tiers.

Unlike drug_eval_script.py (which hard-codes ~9 case-study compounds), this works WITHOUT a
curated list: leave CANDIDATES empty and it ranks ALL compounds (`--compound all`); set
CANDIDATES to restrict the review to a hand-picked cohort. Either way the output is the same
review sheet, ready for human evaluation.

--- HOW THE OUTPUT IS CAPTURED FOR HUMAN EVALUATION ---
The sheet  models/<folder>/drug_eval_results/expert_review_<task>_<ts>.csv  has, per candidate
link, the model evidence PLUS three EMPTY columns the expert fills in a spreadsheet:
    expert_tier       (1 = plausible/known mechanism, 2 = possible, 3 = implausible)
    expert_plausible  (y / n)
    expert_notes      (free text: mechanism, reference, ...)
The expert opens it in Excel/Sheets, fills those columns, saves. Re-run this script with
`aggregate <filled.csv>` to summarise the expert tiers and agreement with the auto tiers.
"""

# ----------------------- CONFIG -----------------------
TASK          = "A"                                              # "A" = DTI (targets), "B" = TREATS (diseases)
MODEL_FOLDER  = os.path.join("models", "REPLACE_WITH_MODEL_FOLDER")
TOPK          = 50

# leave empty -> rank ALL compounds; or pin a curated cohort (entity ids), e.g.:
# CANDIDATES = ["Compound::CHEBI_28918", "Compound::CHEBI_45783", ...]
CANDIDATES = []

# per-task wiring (matches experiments/config.sh)
_CFG = {
    "A": dict(tsv="dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip", task_rel="DTI",    target_type="Protein"),
    "B": dict(tsv="dataset/PKT_subgraphs/pkt_taskB_treats.tsv.zip", task_rel="TREATS", target_type="Disease"),
}
LABELS_TSV = "dataset/PKT_subgraphs/node_labels.tsv"
# ------------------------------------------------------


def run_drug_eval(cfg):
    """Run drug_eval.py for the cohort (all compounds, or one call per curated compound)."""
    common = ["--model_folder", MODEL_FOLDER, "--tsv", cfg["tsv"], "--task", cfg["task_rel"],
              "--target_type", cfg["target_type"], "--topk", str(TOPK)]
    if not CANDIDATES:
        print("[i] No CANDIDATES set -> ranking ALL compounds (--compound all)")
        subprocess.run([sys.executable, "drug_eval.py", *common, "--compound", "all"], check=True)
    else:
        print(f"[i] Ranking {len(CANDIDATES)} curated compounds")
        for i, c in enumerate(CANDIDATES, 1):
            print(f"  [{i}/{len(CANDIDATES)}] {c}")
            r = subprocess.run([sys.executable, "drug_eval.py", *common, "--compound", c])
            if r.returncode != 0:
                print(f"    [WARN] drug_eval exited {r.returncode} for {c}")


def load_all_rankings():
    """Merge every rankings JSON in the model's drug_eval_results/ (newest wins per drug)."""
    files = sorted(glob.glob(os.path.join(MODEL_FOLDER, "drug_eval_results", "*rankings*.json")),
                   key=os.path.getmtime)
    if not files:
        raise SystemExit("No rankings files found — did drug_eval run?")
    merged = {}
    for fp in files:
        with open(fp) as f:
            merged.update(json.load(f))
    print(f"[i] merged {len(merged)} compounds from {len(files)} rankings file(s)")
    return merged


def build_review_sheet(cfg):
    rankings = load_all_rankings()
    if CANDIDATES:
        rankings = {d: p for d, p in rankings.items() if d in set(CANDIDATES)}

    print(f"[i] loading subgraph {cfg['tsv']} for KG-evidence interpretability ...")
    df = load_subgraph(cfg["tsv"])
    ann, heldout = annotate(rankings, df, TASK, TOPK)      # drug/rank/prediction/kg_evidence/auto_tier/...

    labels = {}
    if os.path.exists(LABELS_TSV):
        lab = pd.read_csv(LABELS_TSV, sep="\t", dtype=str)
        labels = dict(zip(lab["entity"], lab["label"]))
    ann["drug_label"] = ann["drug"].map(labels).fillna("")
    ann["prediction_label"] = ann["prediction"].map(labels).fillna("")

    sheet = ann.rename(columns={"drug": "drug_id", "prediction": "prediction_id"})
    sheet = sheet[["drug_id", "drug_label", "rank", "prediction_id", "prediction_label",
                   "confidence", "kg_evidence", "n_evidence", "auto_tier", "held_out_recovered"]]
    # EMPTY columns for the human expert to fill
    sheet["expert_tier"] = ""
    sheet["expert_plausible"] = ""
    sheet["expert_notes"] = ""
    sheet = sheet.sort_values(["drug_id", "rank"])

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = os.path.join(MODEL_FOLDER, "drug_eval_results", f"expert_review_task{TASK}_{ts}.csv")
    sheet.to_csv(out, index=False)
    print(f"\n[i] EXPERT REVIEW SHEET -> {out}")
    print(f"[i] {len(sheet)} candidate links | auto-tier {sheet['auto_tier'].value_counts().to_dict()} | "
          f"held-out recovered: {heldout}")
    print("[i] Fill columns expert_tier / expert_plausible / expert_notes in a spreadsheet, "
          "then: python expert_review_script.py aggregate <filled.csv>")
    return out


def aggregate(filled_csv):
    df = pd.read_csv(filled_csv, dtype=str)
    df["expert_tier"] = pd.to_numeric(df["expert_tier"], errors="coerce")
    rated = df.dropna(subset=["expert_tier"])
    print(f"[aggregate] {filled_csv}")
    print(f"  rated: {len(rated)}/{len(df)}")
    print(f"  expert tier distribution: {rated['expert_tier'].astype(int).value_counts().sort_index().to_dict()}")
    if "auto_tier" in df.columns and len(rated):
        agree = (rated["expert_tier"].astype(int) == pd.to_numeric(rated["auto_tier"]).astype(int)).mean()
        print(f"  auto-vs-expert tier agreement: {agree:.1%}")
    if "expert_plausible" in df.columns:
        pl = rated["expert_plausible"].str.lower().str.startswith("y").sum()
        print(f"  expert-plausible: {pl}/{len(rated)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "aggregate":
        aggregate(sys.argv[2]); sys.exit(0)

    cfg = _CFG[TASK]
    print(f"[i] Task {TASK} | model {MODEL_FOLDER} | target_type {cfg['target_type']} | topk {TOPK}")
    run_drug_eval(cfg)
    build_review_sheet(cfg)
