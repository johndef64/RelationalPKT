"""
drug_eval_results.py

Reads pre-computed drug_eval rankings from the model folder and produces
a summary table (CSV + stdout) with:
- Top-N predicted ExtGene targets per compound
- PubChem metadata (hardcoded)
- Number of known TARGET edges in the KG
- UniProt annotations (protein name, organism, function, subcellular location, pathway)
  fetched via UniProt REST API
"""

import os
import json
import glob
import time
import requests
import pandas as pd

# ── Config ──────────────────────────────────────────────────────────────
model = "target_PathogenKG_n31_core.tsv_20260310_120328"
model_folder = os.path.join("models", model)
results_dir = os.path.join(model_folder, "drug_eval_results")
kg_path = "dataset/PathogenKG_n31_core.tsv.zip"
TOPK = 20
UNIPROT_CACHE_PATH = os.path.join(results_dir, "uniprot_cache.json")

# ── PubChem metadata (hardcoded) ────────────────────────────────────────
PUBCHEM_INFO = {
    "2764":    {"name": "Ciprofloxacin",         "mechanism": "DNA gyrase (GyrA/GyrB) + Topoisomerase IV (ParC/ParE)", "pathway": "DNA replication"},
    "5564":    {"name": "Triclosan",             "mechanism": "FabI / InhA (enoyl-ACP reductase)",                     "pathway": "Fatty acid synthesis"},
    "1990":    {"name": "Acetohydroxamic acid",  "mechanism": "Urease (Ni2+ chelating inhibitor)",                     "pathway": "Virulence metalloenzyme"},
    "2353":    {"name": "Berberine",             "mechanism": "FtsZ + DNA topoisomerase (intercalation)",              "pathway": "Cell division / DNA"},
    "2082":    {"name": "Albendazole",           "mechanism": "beta-tubulin (polymerization inhibitor)",               "pathway": "Cytoskeleton (eukaryotic pathogens)"},
    "5336":    {"name": "Sulfapyridine",         "mechanism": "DHPS (dihydropteroate synthase)",                       "pathway": "Folate biosynthesis"},
    "104838":  {"name": "Imipenem",              "mechanism": "PBP (transpeptidase, cell wall)",                       "pathway": "Bacterial cell wall synthesis"},
    "153241":  {"name": "Merimepodib",           "mechanism": "IMPDH (inosine-5'-monophosphate dehydrogenase)",        "pathway": "Purine biosynthesis"},
    "5459319": {"name": "Virginiamycin M1",      "mechanism": "50S ribosomal (peptidyl-transferase center)",           "pathway": "Protein synthesis"},
    "65781":   {"name": "Ecabet",                "mechanism": "Anti-H. pylori (anti-adhesion + urease)",               "pathway": "Virulence / gastric colonization"},
}


def count_kg_targets(kg_path):
    """Count TARGET edges per compound from the KG."""
    df = pd.read_csv(kg_path, sep='\t')
    target_edges = df[df['interaction'] == 'TARGET']
    return target_edges.groupby('head').size().to_dict()


def load_rankings(results_dir):
    """Load all ranking JSONs, keyed by PubChem ID."""
    rankings = {}
    for fpath in glob.glob(os.path.join(results_dir, "pubchem-*_eval_rankings_*.json")):
        fname = os.path.basename(fpath)
        pcid = fname.split("pubchem-")[1].split("_eval_rankings")[0]
        with open(fpath, 'r') as f:
            data = json.load(f)
        compound_key = list(data.keys())[0]
        rankings[pcid] = data[compound_key]
    return rankings


def _parse_uniprot_entry(entry):
    """Extract relevant fields from a single UniProt API result."""
    uid = entry.get('uniProtkbId', '')
    accession = entry.get('primaryAccession', '')

    # Protein name
    prot_desc = entry.get('proteinDescription', {})
    rec_name = prot_desc.get('recommendedName', {}).get('fullName', {}).get('value', '')
    if not rec_name:
        sub_names = prot_desc.get('submissionNames', [])
        rec_name = sub_names[0]['fullName']['value'] if sub_names else ''
    if not rec_name:
        alt_names = prot_desc.get('alternativeNames', [])
        rec_name = alt_names[0]['fullName']['value'] if alt_names else ''

    # Organism
    organism = entry.get('organism', {}).get('scientificName', '')

    # Comments: function, subcellular location, pathway
    comments = entry.get('comments', [])

    function = ''
    for c in comments:
        if c.get('commentType') == 'FUNCTION':
            texts = c.get('texts', [])
            if texts:
                function = texts[0].get('value', '')
            break

    location = ''
    for c in comments:
        if c.get('commentType') == 'SUBCELLULAR LOCATION':
            locs = c.get('subcellularLocations', [])
            if locs:
                location = locs[0].get('location', {}).get('value', '')
            break

    pathway = ''
    for c in comments:
        if c.get('commentType') == 'PATHWAY':
            texts = c.get('texts', [])
            if texts:
                pathway = texts[0].get('value', '')
            break

    return {
        'accession': accession,
        'protein_name': rec_name,
        'organism': organism,
        'function': function,
        'subcellular_location': location,
        'pathway': pathway,
    }


def fetch_uniprot_annotations(entry_names, cache_path=None, batch_size=20):
    """
    Fetch protein annotations from UniProt REST API in batches.
    Results are cached to avoid repeated API calls.
    """
    # Load cache
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        print(f"[i] Loaded {len(cache)} cached UniProt entries")

    to_fetch = [e for e in entry_names if e not in cache]
    if not to_fetch:
        print(f"[i] All {len(entry_names)} entries found in cache")
        return {e: cache[e] for e in entry_names}

    print(f"[i] Fetching {len(to_fetch)} entries from UniProt API ({len(cache)} cached)...")
    fields = "accession,id,protein_name,organism_name,cc_function,cc_subcellular_location,cc_pathway"

    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i:i + batch_size]
        query = ' OR '.join(['id:' + e for e in batch])
        url = f"https://rest.uniprot.org/uniprotkb/search?query={query}&fields={fields}&format=json&size={len(batch)}"

        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            results = r.json().get('results', [])
            for entry in results:
                uid = entry.get('uniProtkbId', '')
                if uid:
                    cache[uid] = _parse_uniprot_entry(entry)
        except requests.RequestException as e:
            print(f"  [WARNING] API error for batch {i//batch_size + 1}: {e}")

        # Mark entries not returned by API
        for e in batch:
            if e not in cache:
                cache[e] = {
                    'accession': '', 'protein_name': '', 'organism': '',
                    'function': '', 'subcellular_location': '', 'pathway': '',
                }

        if i + batch_size < len(to_fetch):
            time.sleep(0.5)  # rate limiting

        print(f"  batch {i//batch_size + 1}/{(len(to_fetch)-1)//batch_size + 1} done")

    # Save cache
    if cache_path:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)

    return {e: cache[e] for e in entry_names}


if __name__ == "__main__":
    # Load KG target counts
    kg_targets = count_kg_targets(kg_path)

    # Load rankings
    rankings = load_rankings(results_dir)
    print(f"[i] Loaded rankings for {len(rankings)} compounds from {results_dir}\n")

    # Collect all unique predicted targets
    all_target_names = set()
    for pcid in PUBCHEM_INFO:
        if pcid in rankings:
            for p in rankings[pcid][:TOPK]:
                all_target_names.add(p['tail'].replace('ExtGene::Uniprot:', ''))

    # Fetch UniProt annotations
    uniprot_info = fetch_uniprot_annotations(
        sorted(all_target_names), cache_path=UNIPROT_CACHE_PATH
    )

    # ── Build summary table ─────────────────────────────────────────────
    rows = []
    for pcid, info in PUBCHEM_INFO.items():
        compound_key = f"Compound::Pubchem:{pcid}"
        n_targets_kg = kg_targets.get(compound_key, 0)

        if pcid not in rankings:
            print(f"[WARNING] No ranking file for PubChem:{pcid}")
            continue

        top_preds = rankings[pcid][:TOPK]
        for rank_i, pred in enumerate(top_preds, 1):
            gene = pred['tail'].replace('ExtGene::Uniprot:', '')
            score = pred['confidence']
            up = uniprot_info.get(gene, {})

            rows.append({
                'PubChemID': pcid,
                'Compound': info['name'],
                'Mechanism': info['mechanism'],
                'Drug_Pathway': info['pathway'],
                'KG_Targets': n_targets_kg,
                'Pred_Rank': rank_i,
                'Predicted_Target': gene,
                'Confidence': round(score, 4),
                'UniProt_Accession': up.get('accession', ''),
                'Protein_Name': up.get('protein_name', ''),
                'Organism': up.get('organism', ''),
                'Function': up.get('function', ''),
                'Subcellular_Location': up.get('subcellular_location', ''),
                'Target_Pathway': up.get('pathway', ''),
            })

    df = pd.DataFrame(rows)

    # ── Print per-compound summary ──────────────────────────────────────
    for pcid, info in PUBCHEM_INFO.items():
        compound_key = f"Compound::Pubchem:{pcid}"
        n_kg = kg_targets.get(compound_key, 0)
        sub = df[df['PubChemID'] == pcid]
        if sub.empty:
            continue
        print(f"\n{'='*100}")
        print(f"  {info['name']} (PubChem:{pcid})  |  KG targets: {n_kg}")
        print(f"  Mechanism: {info['mechanism']}")
        print(f"  Pathway:   {info['pathway']}")
        print(f"  Top-{TOPK} predicted targets:")
        print(f"  {'Rank':<5} {'Target':<30} {'Conf':>6}  {'Protein Name':<45} {'Organism':<30}")
        print(f"  {'-'*5} {'-'*30} {'-'*6}  {'-'*45} {'-'*30}")
        for _, r in sub.iterrows():
            pname = str(r['Protein_Name'])[:45] if r['Protein_Name'] else '-'
            org = str(r['Organism'])[:30] if r['Organism'] else '-'
            print(f"  {r['Pred_Rank']:<5} {r['Predicted_Target']:<30} {r['Confidence']:>6.4f}  {pname:<45} {org:<30}")
            func = str(r['Function'])[:100] if r['Function'] else ''
            loc = str(r['Subcellular_Location']) if r['Subcellular_Location'] else ''
            tpw = str(r['Target_Pathway']) if r['Target_Pathway'] else ''
            details = []
            if func:
                details.append(f"F: {func}")
            if loc:
                details.append(f"L: {loc}")
            if tpw:
                details.append(f"P: {tpw}")
            if details:
                print(f"  {'':5} {'':30} {'':6}  {' | '.join(details)}")
        print()

    # ── Save CSV ────────────────────────────────────────────────────────
    out_csv = os.path.join(results_dir, "drug_eval_top_predictions.csv")
    df.to_csv(out_csv, index=False)
    print(f"[i] Saved to: {out_csv}")

