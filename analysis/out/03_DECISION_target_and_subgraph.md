# PKT → framework: scelta della relazione TARGET e del sottografo

_Basato su `01_nodes_summary.md`, `02_edges_summary.md`, `02_target_candidates.md`._
PKT: **780.753 nodi**, **11.132.839 archi**, 0 endpoint irrisolti.

---

## 1. Relazione TARGET — DECISIONE

**TARGET = `chemical --[molecularly interacts with]--> protein`**
(ChEBI → Protein Ontology; RO "molecularly interacts with")

| metrica | valore |
|---|---:|
| archi (positivi) | **25.713** |
| farmaci distinti (chemical) | **3.757** |
| bersagli distinti (protein) | **3.496** |

### Perché questa e non le alternative

| candidata | archi | drugs | target | verdetto |
|---|---:|---:|---:|---|
| **chemical–molecularly interacts with→protein** | 25.713 | 3.757 | 3.496 | ✅ **scelta**: interazione molecolare fisica = drug–target nel senso di DrugBank/PathogenKG |
| chemical–interacts with→protein | 71.315 | 4.265 | 7.903 | ⚠️ più ampia ma rumorosa (RO generico, include interazioni indirette/regolatorie) |
| chemical–interacts with→gene | 16.620 | 463 | 11.908 | ⚠️ pochi farmaci (463); target = gene, non proteina |
| protein–type→chemical | 377.333 | 17 | 55.429 | ❌ è `rdf:type` (gerarchia ontologica), non drug–target |

- **Copertura adeguata** (≈ scala di PathogenKG): 3.757 farmaci × 3.496 proteine, 25.713 positivi → sufficiente per link prediction. **Non serve iniettare DrugBank** (Step 0 superato con relazione nativa).
- **Semantica pulita**: `molecularly interacts with` = legame molecolare diretto, l'analogo umano esatto della relazione `TARGET` (drug→protein) di PathogenKG.
- ⚠️ Nota: i 3.757 `chemical` sono entità ChEBI, non tutti farmaci "drug-like". Per la valutazione compound-centric (§3.3) conviene filtrare ai composti drug-like / mappabili a DrugBank; per il training vanno bene tutti.
- ⚠️ Attenzione tecnica: `molecularly interacts with` è **overloaded** — la stessa etichetta indica PPI quando è protein–protein (617k). Il TARGET va definito **type-constrained**: `(chemical, molecularly interacts with, protein)`. Perfetto per la valutazione type-constrained filtered che il framework già usa.

---

## 2. Sottografo da estrarre — PROPOSTA

Substrato protein-centrico, analogo strutturale di PathogenKG (TARGET + PPI + GO + "ponte").
Le relazioni PKT sono memorizzate in coppie inverse: si tiene una direzione.

### Tipi di entità
- **Compound** = `chemical` (CHEBI)
- **Target** = `protein` (PR) — primario; `gene` (EntrezID) opzionale come secondario
- **Contesto** = `go`, `pathway` (opz. `disease`)

### Relazioni da mantenere

| ruolo | relazione (src → tgt) | archi | analogo PathogenKG |
|---|---|---:|---|
| **TARGET** (da predire) | chemical –molecularly interacts with→ protein | 25.713 | `TARGET` |
| **PPI** | protein –molecularly interacts with→ protein | 617.408 | 8 tipi PPI (STRING) |
| **GO** (proc.) | protein –participates in→ go | 129.189 | GO BiologicalProcess |
| **GO** (funz.) | protein –has function→ go | 69.726 | GO MolecularFunction |
| **GO** (loc.) | protein –located_in→ go | 82.463 | GO CellularComponent |
| **Pathway** (ponte) | protein –participates in→ pathway | 117.179 | ORTHOLOGY (come ponte) |
| **Pathway** (ponte) | chemical –participates in→ pathway | 29.860 | — (aggancia i farmaci al contesto) |
| **Pathway** (opz.) | gene –participates in→ pathway | 104.678 | — (aggancia gene, se si include) |

**Totale sottografo core (senza gene/disease): ≈ 1,07M archi** — molto trattabile (PathogenKG ≈ 3M), full-batch RGCN/CompGCN reggono.

### Opzionali (da valutare)
- **disease** come contesto extra: `chemical –is substance that treats→ disease` (168.157), `disease –has phenotype→ phenotype`. Aggiunge segnale di repurposing indicazione-livello; alza scala e n. tipi.
- **gene**: agganciato solo via pathway (sopra) oppure via `rna` (transcribed to / ribosomal translation) — sconsigliato includere `rna` (192k nodi, gonfia il grafo).

### Da ESCLUDERE
- Tutti gli archi `type` (rdf:type, 4,55M = 40,9% del KG): gerarchia ontologica, rumore.
- `rna`, `variant`, `cell`, `anatomy`, `organism`: fuori dominio drug–target, gonfiano scala.

---

## 3. Prossimi passi

1. **Estrazione sottografo** → script `04_extract_subgraph.py`: filtra `edges.json` sulle relazioni sopra, tiene una direzione delle coppie inverse, riduce ai nodi toccati.
2. **Conversione al formato pipeline** (TSV `head / interaction / tail` o HeteroData) atteso da `train_and_eval.py`, con mapping tipi/relazioni (Compound/Target + TARGET + relazioni di contesto).
3. **Run identico** del framework: R-GCN + CompGCN, DistMult, focal loss + adversarial neg, split edge-level multi-seed, metriche AUROC/AUPRC/MRR/Hits@k, valutazione type-constrained filtered su `TARGET`.
