# RelationalPKT — Heterogeneous KG Link Prediction for Drug Repurposing on PheKnowLator

[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![PyG](https://img.shields.io/badge/PyTorch_Geometric-2.0+-3C2179?logo=pytorch&logoColor=white)](https://pytorch-geometric.readthedocs.io/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**RelationalPKT applies the PathogenKG method — heterogeneous knowledge-graph link prediction
for drug repurposing (R-GCN / CompGCN encoders + DistMult decoder) — to the human
[PheKnowLator](https://github.com/callahantiff/PheKnowLator) (PKT) knowledge graph.**

PathogenKG was developed and validated in the *bacterial* domain (STRING PPI + COG orthology +
GO + DrugBank). RelationalPKT reuses the **same code and the same experimental protocol**,
unchanged, on a *human* biomedical KG — turning the method into a real, human-domain component of
the framework instead of a separate bacterial graph. The encoders use **lookup embeddings (no node
features)**, so the featureless PKT nodes are used as-is: this is the topology-only setting.

---

## Two repurposing tasks

The same link-prediction machinery is run on two target relations, selected after analysing the KG
(native coverage is sufficient — no external DrugBank injection needed):

| Task | Target relation | Meaning | Edges | Drugs | Targets |
|---|---|---|---:|---:|---:|
| **A — DTI** | `Compound → Protein` (`molecularly interacts with`) | mechanistic drug–target | 25,713 | 3,757 | 3,496 proteins |
| **B — TREATS** | `Compound → Disease` (`is substance that treats`) | canonical drug–disease repurposing | 168,157 | 4,328 | 4,480 diseases |

Task A mirrors PathogenKG's `TARGET`; Task B is the classic human repurposing formulation
(Hetionet / DRKG / TxGNN lineage). Both can also be trained jointly (`--task DTI,TREATS`).
There is **no pharmacological drug–drug (DDI)** relation in PKT (chemical–chemical edges are ChEBI
structural only).

---

## The PheKnowLator (PKT) knowledge graph

Human biomedical KG in `dataset/PKT/` as `nodes.json` (~483 MB) + `edges.json` (~4.6 GB), streamed
with `ijson`.

- **780,753 nodes**, **11,132,839 edges**, 0 unresolved endpoints.
- Node types: rna 192,975 · **chemical 150,326** (ChEBI) · variant 144,966 · **protein 96,085** (PR) ·
  go 43,823 · **gene 27,328** (Entrez) · **disease 23,384** (MONDO) · pathway 16,382 · phenotype 17,121.
- `rdf:type` is 40.9% of edges (ontology hierarchy → dropped); predicates are stored as inverse pairs
  (only one direction is kept — the framework re-adds reverse edges internally).

Full analysis in [`analysis/out/`](analysis/out/) (`01_nodes_summary.md`, `02_edges_summary.md`,
`04_relazioni_canoniche_e_scelta_target.md`).

---

## Task subgraphs

Two task-specific subgraphs are extracted from PKT into the exact TSV format the framework expects
(`head <TAB> interaction <TAB> tail`, entity = `Type::id`), sharing an identical molecular **CORE**
(PPI + protein→GO + pathway + gene↔protein bridge):

| Subgraph | file | edges | nodes | run with |
|---|---|---:|---:|---|
| Task A | `dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip` | 1,136,665 | 66,961 | `--task DTI` |
| Task B | `dataset/PKT_subgraphs/pkt_taskB_treats.tsv.zip` | 1,853,908 | 93,831 | `--task TREATS` |
| Unified | `dataset/PKT_subgraphs/pkt_unified.tsv.zip` | = Task B | = Task B | `--task DTI,TREATS` |

Two correctness steps during extraction: relations are **renamed type-constrained** (fixing the
`molecularly interacts with` overloading → distinct `PPI` / `DTI` / `COMPOUND_GO`), and each inverse
pair is reduced to one direction (symmetric PPI deduped 617k → 308,704). Built by
[`analysis/06_build_subgraphs.py`](analysis/06_build_subgraphs.py); stats in
[`analysis/out/06_subgraph_stats.md`](analysis/out/06_subgraph_stats.md).

---

## Repository structure

```
RelationalPKT/
├── train_and_eval.py            # training & evaluation (added: --config)
├── drug_eval.py                 # compound-centric repurposing eval (added: --target_type)
├── drug_eval_results.py         # summarise drug-eval outputs
├── tuning_hyperparameter.py     # Bayesian W&B HPO (logs to project RelationalPKT)
├── expert_review_script.py      # human 3-tier expert review driver (cohort → review sheet)
├── src/                         # encoders (hetero_rgcn/compgcn/rgat), utils, metrics, params
│
├── dataset/
│   ├── PKT/                     # raw PheKnowLator KG (nodes.json + edges.json, zipped)
│   └── PKT_subgraphs/           # built task subgraphs (+ ablation/, node_labels.tsv)
│
├── analysis/                    # KG analysis & subgraph builders (01–08_*.py) + out/
├── experiments/                 # server run scripts (E1–E4), config, interpret_predictions.py, README
└── docs/                        # project report + expert-validation request docs
```

---

## Environment setup

Use the conda env **`gnn`** (already provisioned with all requirements). To recreate from scratch:

```bash
conda create -n gnn python=3.10 -y && conda activate gnn
pip install -r requirements.txt
```

If `torch-sparse` fails, install PyTorch/PyG wheels separately (match your CUDA, e.g. `cu128`):

```bash
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
pip install --no-cache-dir --only-binary=:all: \
  pyg_lib torch-geometric torch-scatter torch-sparse torch-cluster torch-spline-conv \
  termcolor torcheval -f https://data.pyg.org/whl/torch-2.7.1+cu128.html
```

**Requirements:** Python 3.10, a CUDA GPU with adequate VRAM (the full-graph ranking needs a real
GPU — see the TDR note in `experiments/README.md`). Full experiment runs are meant for the **server**.

---

## Quick start

```bash
conda activate gnn

# 1. Build the task subgraphs from PKT (one-time)
python analysis/06_build_subgraphs.py

# 2. Train (Task A / DTI, CompGCN, BIOKG-128 config)
python train_and_eval.py --tsv dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip \
  --task DTI --model compgcn --config BIOKG-128 --runs 12 --epochs 400 \
  --early_stopping --negative_sampling filtered --eval_filtered

# 3. Compound-centric repurposing on a trained model (Task A ranks proteins)
python drug_eval.py --model_folder models/<your_model_folder> \
  --tsv dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip --task DTI --target_type Protein --compound all
```

Full, scripted pipeline (both tasks, HPO, ablations, repurposing) lives in
**[`experiments/`](experiments/)** — see [`experiments/README.md`](experiments/README.md).

| Exp | What | Script |
|---|---|---|
| **E1** | main training & model comparison (compgcn/rgcn, 12 seeds) | `experiments/e1_main_training.sh` |
| **E2** | Bayesian hyperparameter optimisation (W&B) | `experiments/e2_hpo_sweep.sh` |
| **E3** | ablations (component machinery + relational context) | `experiments/e3_ablation.sh` |
| **E4** | compound-centric repurposing + interpretability + expert review | `experiments/e4_repurposing.sh` |

Evaluation protocol (unchanged from PathogenKG): edge-level stratified split, multi-seed, focal loss
(α=0.25, γ=3.0) + adversarial negative weighting (α_adv=2.0), oversample ×5 / undersample ×0.5,
type-constrained **filtered** metrics — AUROC, AUPRC, MRR, Hits@1/3/10 and composite
**M = 0.2·AUROC + 0.4·AUPRC + 0.4·MRR**.

---

## Interpretability vs validation

A deliberate, honest distinction (see `experiments/README.md` for the full discussion):

- **Held-out filtered metrics** — non-circular quantitative validation (hide known edges, measure
  recovery).
- **`experiments/interpret_predictions.py`** — **interpretability, not validation.** It surfaces KG
  evidence for each novel link (shared PPI / pathway / GO for Task A; molecular meta-path + phenotype
  overlap for Task B). This evidence is *circular* w.r.t. the model (same graph it trained on): it
  explains *why*, it does not prove *true*.
- **`expert_review_script.py`** — human 3-tier review (PathogenKG §5 style): brings knowledge
  *external* to the KG, which is what genuinely breaks the circularity. Produces a review sheet with
  empty `expert_tier / expert_plausible / expert_notes` columns; clinician request docs are in
  [`docs/`](docs/).
- A **time-split** (train on an older PheKnowLator release, test on later-added edges) would be the
  strongest automatic external validation — proposed, not yet built.

---

## Documentation

- [`docs/report_progetto_RelationalPKT.md`](docs/report_progetto_RelationalPKT.md) — full project report.
- [`docs/richiesta_candidati_validazione_medico.md`](docs/richiesta_candidati_validazione_medico.md) — candidate request for a clinician/biologist.
- [`docs/richiesta_candidati_validazione_oncologo.md`](docs/richiesta_candidati_validazione_oncologo.md) — oncology-tailored version (with TCGA / multi-omics cross-check).
- [`experiments/README.md`](experiments/README.md) — experiment plan and run instructions.

---

## Credits & upstream

RelationalPKT builds directly on the **PathogenKG** codebase and method
(De Filippis, Tommasino, Rinaldi — *PathogenKG: Cross-Species Drug Repurposing via Heterogeneous
Knowledge Graph Link Prediction*, ECML PKDD 2026). The knowledge graph is
**[PheKnowLator](https://github.com/callahantiff/PheKnowLator)**.

## License

MIT — see [LICENSE](LICENSE).
