"""
06_build_subgraphs.py
---------------------
Extract task-specific repurposing subgraphs from the PKT KG and write them in the
EXACT format the PathogenKG framework expects:

    TSV  head <TAB> interaction <TAB> tail <TAB> source <TAB> type
    entity = "<Type>::<entity_id>"   (node type = prefix before "::")

The framework (src/utils.load_data / set_target_label) uses ONLY head/interaction/tail;
node types come from the "::" prefix; the task target is selected at runtime by
`--task <INTERACTION_NAME>`. So we:

  * RENAME relations to be type-constrained (fixes the "molecularly interacts with"
    overloading: it is PPI between proteins, DTI between chemical+protein, drug-GO
    between chemical+go — here they become distinct interaction names PPI / DTI / COMPOUND_GO).
  * Keep ONE direction of every inverse pair (the framework re-adds reverse edges itself).
  * De-duplicate; symmetric same-type relations (PPI) are deduped as unordered pairs.

Outputs (dataset/PKT_subgraphs/):
  pkt_taskA_dti.tsv.zip      TASK A: predict DTI  (chemical -> protein)   --task DTI
  pkt_taskB_treats.tsv.zip   TASK B: predict TREATS (chemical -> disease) --task TREATS
  pkt_unified.tsv.zip        both targets + all context (multi-task)      --task DTI,TREATS
  06_subgraph_stats.md       per-relation / per-task statistics

Run in conda env `gnn`.  Toggle INCLUDE_VARIANT below to add the genetic (variant) layer to
Task B / unified (heavier: ~145k extra nodes -> use neighbor sampling downstream if enabled).
"""
import ijson
import zipfile
import csv
import io
from pathlib import Path
from collections import defaultdict

PKT_DIR = Path(__file__).resolve().parents[1] / "dataset" / "PKT"
OUT_DIR = Path(__file__).resolve().parents[1] / "dataset" / "PKT_subgraphs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
STATS_MD = Path(__file__).resolve().parent / "out" / "06_subgraph_stats.md"

INCLUDE_VARIANT = False   # add variant->gene / variant->disease layer to Task B & unified

# node bioentity_type -> entity string prefix (node type seen by the framework)
TYPE_PREFIX = {
    "chemical": "Compound",
    "protein":  "Protein",
    "gene":     "Gene",
    "go":       "GO",
    "pathway":  "Pathway",
    "disease":  "Disease",
    "phenotype":"Phenotype",
    "variant":  "Variant",
}

# (src_type, predicate_label, tgt_type) -> (relation_name, symmetric)
# relation_name is the type-constrained interaction written to the TSV.
RELATION_MAP = {
    # ---- targets ----
    ("chemical", "molecularly interacts with", "protein"):        ("DTI", False),      # TASK A target
    ("chemical", "is substance that treats",   "disease"):        ("TREATS", False),   # TASK B target
    # ---- molecular CORE (shared by both tasks) ----
    ("protein", "molecularly interacts with", "protein"):         ("PPI", True),
    ("protein", "participates in", "go"):                         ("PROTEIN_GO_PROCESS", False),
    ("protein", "has function", "go"):                            ("PROTEIN_GO_FUNCTION", False),
    ("protein", "located_in", "go"):                              ("PROTEIN_GO_COMPONENT", False),
    ("protein", "participates in", "pathway"):                    ("PROTEIN_PATHWAY", False),
    ("gene", "has gene product", "protein"):                      ("GENE_PRODUCT", False),   # gene<->protein bridge
    # ---- drug-side context (both tasks) ----
    ("chemical", "molecularly interacts with", "go"):             ("COMPOUND_GO", False),
    ("chemical", "participates in", "pathway"):                   ("COMPOUND_PATHWAY", False),
    # ---- disease layer (TASK B) ----
    ("gene", "participates in", "pathway"):                       ("GENE_PATHWAY", False),
    ("gene", "causes or contributes to condition", "disease"):    ("GDA", False),
    ("disease", "disease has basis in dysfunction of", "gene"):   ("GDA_DYSFUNCTION", False),
    ("disease", "has phenotype", "phenotype"):                    ("DISEASE_PHENOTYPE", False),
    # ---- genetic/variant layer (optional, TASK B) ----
    ("variant", "causally influences", "gene"):                   ("VARIANT_GENE", False),
    ("variant", "causes or contributes to condition", "disease"): ("VARIANT_DISEASE", False),
}

CORE = {"PPI", "PROTEIN_GO_PROCESS", "PROTEIN_GO_FUNCTION", "PROTEIN_GO_COMPONENT",
        "PROTEIN_PATHWAY", "GENE_PRODUCT", "COMPOUND_GO", "COMPOUND_PATHWAY"}

TASK_A = CORE | {"DTI"}
TASK_B = CORE | {"TREATS", "DTI", "GENE_PATHWAY", "GDA", "GDA_DYSFUNCTION", "DISEASE_PHENOTYPE"}
VARIANT_RELS = {"VARIANT_GENE", "VARIANT_DISEASE"}
if INCLUDE_VARIANT:
    TASK_B |= VARIANT_RELS
UNIFIED = TASK_A | TASK_B

NEEDED_TYPES = set(TYPE_PREFIX) if INCLUDE_VARIANT else (set(TYPE_PREFIX) - {"variant"})


def build_node_lookup():
    """uri -> 'Type::entity_id' for the node types we need."""
    print("Reading nodes.json ...", flush=True)
    uri2node = {}
    with zipfile.ZipFile(PKT_DIR / "nodes.zip") as z, z.open("nodes.json") as f:
        for o in ijson.items(f, "item"):
            bt = o.get("bioentity_type")
            if bt in NEEDED_TYPES:
                eid = o.get("entity_id")
                if eid:
                    uri2node[o["uri"]] = f"{TYPE_PREFIX[bt]}::{eid}"
    print(f"  mapped {len(uri2node):,} nodes", flush=True)
    return uri2node


def extract_edges(uri2node):
    """Stream edges once; return {relation_name: set of (head, tail)} deduped."""
    edges = defaultdict(set)
    n = 0
    with zipfile.ZipFile(PKT_DIR / "edges.zip") as z, z.open("edges.json") as f:
        for e in ijson.items(f, "item"):
            n += 1
            s_uri = e.get("source_uri"); t_uri = e.get("target_uri")
            # classify by bioentity_type via the prefix we stored — need raw types:
            # reconstruct type from mapped string prefix is possible, but we keyed
            # RELATION_MAP on raw bioentity_type, so look them up from the map key using
            # node strings' prefixes.
            hs = uri2node.get(s_uri); ts = uri2node.get(t_uri)
            if hs is None or ts is None:
                continue
            s_type = PREFIX2TYPE[hs.split("::", 1)[0]]
            t_type = PREFIX2TYPE[ts.split("::", 1)[0]]
            spec = RELATION_MAP.get((s_type, e.get("predicate_label"), t_type))
            if spec is None:
                continue
            rel, symmetric = spec
            if symmetric:
                a, b = (hs, ts) if hs <= ts else (ts, hs)
                if a == b:      # drop self loops (framework adds its own)
                    continue
                edges[rel].add((a, b))
            else:
                edges[rel].add((hs, ts))
            if n % 2_000_000 == 0:
                print(f"  ...{n:,} edges scanned", flush=True)
    print(f"Total edges scanned: {n:,}")
    return edges


def write_subgraph(name, rel_names, edges):
    """Write dataset/PKT_subgraphs/<name>.tsv.zip for the given relation set."""
    tsv_name = f"{name}.tsv"
    zip_path = OUT_DIR / f"{name}.tsv.zip"
    n_edges = 0
    node_types = defaultdict(set)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    w.writerow(["head", "interaction", "tail", "source", "type"])
    for rel in sorted(rel_names):
        for h, t in edges.get(rel, ()):
            ht = h.split("::", 1)[0]; tt = t.split("::", 1)[0]
            w.writerow([h, rel, t, "PKT", f"{ht}-{tt}"])
            node_types[ht].add(h); node_types[tt].add(t)
            n_edges += 1
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(tsv_name, buf.getvalue())
    return n_edges, {k: len(v) for k, v in node_types.items()}


PREFIX2TYPE = {v: k for k, v in TYPE_PREFIX.items()}


def main():
    uri2node = build_node_lookup()
    edges = extract_edges(uri2node)

    # per-relation counts
    rel_counts = {rel: len(s) for rel, s in edges.items()}

    outputs = {
        "pkt_taskA_dti":    ("TASK A — predict DTI (chemical->protein)",   TASK_A),
        "pkt_taskB_treats": ("TASK B — predict TREATS (chemical->disease)", TASK_B),
        "pkt_unified":      ("UNIFIED — both targets (multi-task)",         UNIFIED),
    }
    results = {}
    for name, (desc, rels) in outputs.items():
        ne, ntypes = write_subgraph(name, rels, edges)
        results[name] = (desc, rels, ne, ntypes)
        print(f"[{name}] {ne:,} edges  nodes={ntypes}")

    # stats markdown
    with open(STATS_MD, "w", encoding="utf-8") as fh:
        fh.write("# PKT subgraphs — build statistics\n\n")
        fh.write(f"INCLUDE_VARIANT = {INCLUDE_VARIANT}\n\n")
        fh.write("## De-duplicated edges per relation (one direction kept)\n\n")
        fh.write("| relation | edges | in A | in B | in unified |\n|---|---:|:--:|:--:|:--:|\n")
        for rel in sorted(rel_counts):
            fh.write(f"| {rel} | {rel_counts[rel]:,} | "
                     f"{'✓' if rel in TASK_A else ''} | {'✓' if rel in TASK_B else ''} | "
                     f"{'✓' if rel in UNIFIED else ''} |\n")
        fh.write("\n## Per-subgraph totals\n\n")
        for name, (desc, rels, ne, ntypes) in results.items():
            fh.write(f"### {name}  — {desc}\n\n")
            fh.write(f"- file: `dataset/PKT_subgraphs/{name}.tsv.zip`\n")
            fh.write(f"- relations: {sorted(rels)}\n")
            fh.write(f"- **edges: {ne:,}**\n")
            fh.write(f"- nodes per type: {ntypes}\n")
            fh.write(f"- total nodes: {sum(ntypes.values()):,}\n\n")
    print(f"\nSaved stats -> {STATS_MD}")


if __name__ == "__main__":
    main()
