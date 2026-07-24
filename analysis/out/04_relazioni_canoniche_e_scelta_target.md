# PKT — Fase 1: risultati analisi e scelta della relazione da predire

_Sintesi delle due valutazioni: (A) esito Fase 1 con TARGET drug–target, (B) valutazione
delle relazioni più canoniche nei KG biomedici umani. Dati da `01_nodes_summary.md`,
`02_edges_summary.md`, `02_target_candidates.md`, `03_DECISION_target_and_subgraph.md`._

---

## A. Esito Fase 1 — analisi PKT e scelta TARGET (drug–target)

### PKT in numeri
**780.753 nodi · 11.132.839 archi · 0 endpoint irrisolti** (lookup uri→tipo perfetta).
Attenzione: il 40,9% degli archi è `type` (rdf:type = gerarchia ontologica, rumore da
scartare), e i predicati sono in coppie inverse (tenere una direzione).

### Relazione TARGET scelta (opzione drug–target)
**`chemical —[molecularly interacts with]→ protein`** (ChEBI → Protein Ontology)

| | valore |
|---|---:|
| archi (positivi) | **25.713** |
| farmaci distinti | **3.757** |
| proteine bersaglio distinte | **3.496** |

**Perché questa** tra le candidate:
- È l'interazione **molecolare fisica** = il vero drug–target, analogo umano esatto del
  `TARGET` di PathogenKG.
- Le alternative sono peggiori: `interacts with→protein` (71k) è più ampia ma rumorosa;
  `interacts with→gene` ha solo 463 farmaci; `type→protein` (377k) è rdf:type, non
  drug-target.
- **Copertura sufficiente** (scala simile a PathogenKG) → **Step 0 superato: non serve
  iniettare DrugBank**, la relazione nativa basta.
- ⚠️ `molecularly interacts with` è overloaded (indica anche PPI tra proteine, 617k) → il
  TARGET va definito **type-constrained** `(chemical, ..., protein)` — cosa che il
  framework già gestisce nella valutazione filtered.

### Sottografo proposto (~1,07M archi, trattabile)
Protein-centrico, analogo strutturale di PathogenKG:
- **TARGET**: chemical→protein (25.713) — da predire
- **PPI**: protein→protein `molecularly interacts with` (617k) — come STRING
- **GO**: protein→go `participates in` / `has function` / `located_in` (~281k) — i 3 tipi GO
- **Pathway** (fa da "ponte" al posto dell'ortologia): protein/chemical/gene →pathway
  `participates in`
- Da **escludere**: tutti gli archi `type`, più rna/variant/cell/anatomy (fuori dominio,
  gonfiano la scala)

---

## B. Valutazione: quali relazioni sono più canoniche nei KG biomedici umani?

Le task di link prediction più predette in letteratura (Hetionet/Rephetio, DRKG,
OpenBioLink, PrimeKG, BioKG…), in ordine di "canonicità" per il **drug repurposing**:

**1. Drug → Disease ("treats" / indicazione) — LA task di repurposing per antonomasia.**
È letteralmente la definizione di repurposing: predire nuove coppie farmaco–malattia curabile.
- Landmark: **Himmelstein et al. 2017 (Hetionet / Rephetio)** — `Compound–treats–Disease`;
  **DRKG** (repurposing COVID-19); **TxGNN, Zitnik lab 2023** (zero-shot repurposing su
  PrimeKG, stato dell'arte).
- **In PKT:** `chemical –is substance that treats→ disease` = **168.157 archi** (+ 109.818
  verso `phenotype`). È la relazione drug-centrica **più densa** del KG dopo la PPI.

**2. Drug → Target (DTI) — quella scelta in sezione A.**
Repurposing *meccanicistico*: predici il bersaglio molecolare, il repurposing è inferito.
- Landmark: DeepDTnet, DTINet, NeoDTI, benchmark DTI (DrugBank, BindingDB).
- **In PKT:** `chemical –molecularly interacts with→ protein` = **25.713**
  (3.757 farmaci × 3.496 proteine).

**3. Gene/Protein → Disease (GDA) — canonica per *target discovery*, non repurposing.**
- Landmark: DisGeNET, Open Targets, PrimeKG.
- **In PKT:** sparsa — `disease –has basis in dysfunction of→` 4.594;
  `variant –causes/contributes to condition→ disease` 43.013 (indiretta, via varianti).

**4. PPI (protein→protein) e Protein→Pathway/GO — network biology, non repurposing.**
- **In PKT:** PPI 617.408, GO/pathway ~500k. Sono il **contesto** ideale, non il bersaglio
  da predire.

### Cosa cambia rispetto a PathogenKG
Punto chiave: **PathogenKG ha usato DTI perché era batterico — lì non esiste un nodo
"malattia"**, il target *è* l'obiettivo terapeutico. In un KG **umano** si sblocca la
relazione `treats` diretta, la formulazione di repurposing più classica e più abbondante
nei dati (168k vs 25k).

| | **Drug→Target (DTI)** — sezione A | **Drug→Disease ("treats")** — alternativa canonica |
|---|---|---|
| Fedeltà al metodo PathogenKG | ✅ identica (method→application pulito) | ⚠️ stesso *codice*, ma task diverso da quello del paper |
| Canonicità repurposing umano | media (meccanicistico) | ✅ **massima** (Hetionet/DRKG/TxGNN) |
| Densità dati (PKT) | 25.713 | **168.157** |
| Interpretazione | farmaco→proteina (serve poi legare a malattia) | farmaco→malattia (repurposing diretto) |
| Validazione biologica | ranking proteine (come nel paper) | ranking malattie/indicazioni (held-out treats) |

**Nota metodologica:** la scelta non è esclusiva. Il framework accetta `--task` con **una o
più** relazioni, quindi si può:
- **A)** restare su **DTI** (fedeltà massima al paper, ponte pulito batterico→umano);
- **B)** passare a **Drug→Disease "treats"** (repurposing umano più canonico e con più dati);
- **C)** **doppio task**: predire `treats` come primario e `molecularly interacts with` come
  secondario/meccanicistico — copre sia l'indicazione che il razionale molecolare.

### Raccomandazione
Se l'obiettivo della tesi è **"repurposing sul substrato umano"** e serve il framing più
solido in letteratura → **Drug→Disease "treats" come relazione TARGET primaria**, con DTI
(chemical→protein) tenuta come relazione di **contesto**. È la task più canonica *e* la più
ricca di dati in PKT.
Se invece la priorità è **"stesso metodo del paper, zero deviazioni"** → restare su DTI.

### Copertura delle relazioni TARGET candidate (misurata su edges.json)

_Fonte: `05_coverage_candidates.csv`._

| relazione TARGET | archi | farmaci distinti | bersagli distinti |
|---|---:|---:|---:|
| **drug→disease** `is substance that treats` | **168.157** | **4.328** | **4.480** (malattie) |
| drug→phenotype `is substance that treats` | 109.818 | 4.094 | 1.731 (fenotipi) |
| drug→protein (DTI) `molecularly interacts with` | 25.713 | 3.757 | 3.496 (proteine) |
| drug→protein (broad) `interacts with` | 71.315 | 4.265 | 7.903 |
| drug→gene (broad) `interacts with` | 16.620 | 463 | 11.908 |

**Esito:** `drug→disease "treats"` ha copertura **superiore** al DTI — più farmaci
(4.328 vs 3.757) e 4.480 malattie bersaglio. Densità ~0,87% (168k su 4.328×4.480):
adatta al link prediction. **Fattibilità confermata anche per il task B**, senza iniezioni
esterne. La scelta tra A e B è quindi metodologica (fedeltà al paper vs canonicità/dati),
non di fattibilità: entrambe reggono.

---

## C. Altre relazioni utili da aggiungere al sottografo (per i due task)

_Copertura da `05_coverage_candidates.csv`. Le relazioni sono in coppie inverse: se ne tiene una._

### Drug–drug (DDI): **NON disponibile in PKT**
Non esiste alcuna interazione farmaco–farmaco *farmacologica*. Tutte le relazioni
chemical–chemical sono **ChEBI strutturali/ontologiche**, non terapeutiche:

| relazione chem–chem | archi | natura |
|---|---:|---|
| `has_role` | 41.433 | ruolo ChEBI (es. "antibiotico") — ontologica |
| `has functional parent` | 17.602 | gerarchia strutturale |
| `is conjugate acid/base of` | 8.162 | chimica acido-base |
| `has part` | 3.879 | struttura molecolare |
| `is enantiomer of` | 2.654 | stereochimica |

→ **Da NON aggiungere** (stessa logica con cui si scarta `rdf:type`: gonfiano con rumore
ontologico, non danno segnale di repurposing). Se in futuro servisse una DDI reale, andrebbe
**iniettata da fonte esterna** (DrugBank/TWOSIDES) — fuori scope ora.

### Relazioni di contesto raccomandate

**Comuni a entrambi i task (strato molecolare):**

| relazione (src→tgt) | archi | d_src | d_tgt | ruolo |
|---|---:|---:|---:|---|
| protein –molecularly interacts with→ protein | 617.408 | 14.208 | 14.208 | **PPI** (rete proteica, come STRING) |
| protein –participates in→ go | 129.189 | 17.385 | 12.311 | GO biological process |
| protein –has function→ go | 69.726 | 17.777 | 4.424 | GO molecular function |
| protein –located_in→ go | 82.463 | 18.434 | 1.752 | GO cellular component |
| protein –participates in→ pathway | 117.179 | 10.502 | 2.492 | pathway (ponte) |
| gene –has gene product→ protein | 19.478 | 19.273 | 19.091 | **bridge gene↔protein** (~1:1, unifica i due strati) |

**Utili soprattutto per il TASK A (DTI) — arricchiscono il lato farmaco:**

| relazione | archi | d_src | d_tgt | nota |
|---|---:|---:|---:|---|
| chemical –molecularly interacts with→ go | 354.353 | 1.365 | 1.928 | drug→GO (copre 1.365/3.757 farmaci) |
| chemical –participates in→ pathway | 29.860 | 2.240 | 2.241 | drug→pathway |

**Necessarie per il TASK B (drug→disease) — collegano lo strato molecolare alla malattia:**

| relazione | archi | d_src | d_tgt | ruolo |
|---|---:|---:|---:|---|
| chemical –molecularly interacts with→ protein (DTI) | 25.713 | 3.757 | 3.496 | ponte farmaco→bersaglio |
| gene –causes/contributes to condition→ disease | 12.757 | 5.031 | 4.398 | **GDA** gene→malattia |
| disease –has basis in dysfunction of→ gene | 4.494 | 4.460 | 3.348 | GDA (inversa) |
| gene –participates in→ pathway | 104.678 | 10.358 | 1.807 | pathway lato gene |
| disease –has phenotype→ phenotype | 427.157 | 11.763 | 10.051 | **similarità malattie via fenotipi condivisi** (segnale repurposing forte, à la Hetionet) |
| variant –causally influences→ gene | 144.892 | 144.892 | 3.617 | strato genetico (⚠️ +144k nodi variant) |
| variant –causes/contributes to condition→ disease | 43.013 | 14.693 | 3.677 | genetica→malattia (⚠️ scala) |

### Sintesi operativa
- **Task A (DTI):** sottografo core (§A) **+ drug→GO, drug→pathway, gene↔protein bridge**.
  Resta ~1,1–1,4M archi, molto trattabile.
- **Task B (drug→disease):** aggiungi lo **strato malattia**: DTI + GDA (gene↔disease) +
  disease→phenotype + gene↔protein bridge + gene→pathway. Valuta se includere lo strato
  `variant` (dà segnale genetico ma aggiunge ~145k nodi → usare neighbor sampling se incluso).
- **Disease–disease:** non esiste una relazione diretta significativa; la similarità tra
  malattie si ottiene **via fenotipi condivisi** (`disease→has phenotype→phenotype`), che è
  l'approccio canonico.
- **Da escludere sempre:** `rdf:type` e le relazioni chem–chem strutturali (rumore ontologico).
