"""
07_build_ablation_subgraphs.py
------------------------------
Generate RELATIONAL-CONTEXT ablation variants of a task subgraph by filtering the
already-built TSV (fast: no re-scan of the 4.6 GB edges.json).

Each variant keeps the TARGET relation and a subset of the context relations, so we can
measure how much each context layer (PPI / GO / pathway / drug-context) contributes to
link prediction — the "topology-only" ablation of the PathogenKG method on PKT.

Variants for Task A (DTI target = 'DTI'):
  full        all relations (== dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip)
  core_ppi    DTI + PPI only                       (bare protein network)
  no_ppi      full minus PPI
  no_go       full minus the 3 protein-GO relations
  no_pathway  full minus pathway relations
  no_drugctx  full minus COMPOUND_GO / COMPOUND_PATHWAY (drug only via DTI)

Run in conda env `gnn`.  Outputs to dataset/PKT_subgraphs/ablation/.
"""
import pandas as pd
import zipfile
import io
from pathlib import Path

SUB_DIR = Path(__file__).resolve().parents[1] / "dataset" / "PKT_subgraphs"
ABL_DIR = SUB_DIR / "ablation"
ABL_DIR.mkdir(parents=True, exist_ok=True)

BASE = SUB_DIR / "pkt_taskA_dti.tsv.zip"   # DTI task graph as the ablation base
TARGET_REL = "DTI"

GO_RELS = {"PROTEIN_GO_PROCESS", "PROTEIN_GO_FUNCTION", "PROTEIN_GO_COMPONENT"}
PATHWAY_RELS = {"PROTEIN_PATHWAY", "COMPOUND_PATHWAY", "GENE_PATHWAY"}
DRUGCTX_RELS = {"COMPOUND_GO", "COMPOUND_PATHWAY"}


def write_variant(df, rels_keep, name):
    sub = df[df["interaction"].isin(rels_keep)]
    buf = io.StringIO()
    sub.to_csv(buf, sep="\t", index=False)
    with zipfile.ZipFile(ABL_DIR / f"{name}.tsv.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}.tsv", buf.getvalue())
    n_t = int((sub["interaction"] == TARGET_REL).sum())
    print(f"  {name:28s} edges={len(sub):>9,}  target({TARGET_REL})={n_t:,}  rels={sorted(rels_keep)}")
    return name, len(sub), n_t


def main():
    print(f"Loading base {BASE.name} ...")
    df = pd.read_csv(BASE, sep="\t", dtype=str, compression="zip")
    all_rels = set(df["interaction"].unique())
    print(f"  {len(df):,} edges, relations: {sorted(all_rels)}\n")

    variants = {
        "pkt_ablA_full":       all_rels,
        "pkt_ablA_core_ppi":   {TARGET_REL, "PPI"},
        "pkt_ablA_no_ppi":     all_rels - {"PPI"},
        "pkt_ablA_no_go":      all_rels - GO_RELS,
        "pkt_ablA_no_pathway": all_rels - PATHWAY_RELS,
        "pkt_ablA_no_drugctx": all_rels - DRUGCTX_RELS,
    }
    print("Writing ablation variants:")
    rows = [write_variant(df, rels, name) for name, rels in variants.items()]

    with open(ABL_DIR / "ablation_index.md", "w", encoding="utf-8") as fh:
        fh.write("# Task A (DTI) — relational-context ablation subgraphs\n\n")
        fh.write("| variant | file | edges | target edges |\n|---|---|---:|---:|\n")
        for name, ne, nt in rows:
            fh.write(f"| {name} | `dataset/PKT_subgraphs/ablation/{name}.tsv.zip` | {ne:,} | {nt:,} |\n")
    print(f"\nSaved -> {ABL_DIR/'ablation_index.md'}")


if __name__ == "__main__":
    main()
