# PKT subgraphs — build statistics

INCLUDE_VARIANT = False

## De-duplicated edges per relation (one direction kept)

| relation | edges | in A | in B | in unified |
|---|---:|:--:|:--:|:--:|
| COMPOUND_GO | 354,353 | ✓ | ✓ | ✓ |
| COMPOUND_PATHWAY | 29,860 | ✓ | ✓ | ✓ |
| DISEASE_PHENOTYPE | 427,157 |  | ✓ | ✓ |
| DTI | 25,713 | ✓ | ✓ | ✓ |
| GDA | 12,757 |  | ✓ | ✓ |
| GDA_DYSFUNCTION | 4,494 |  | ✓ | ✓ |
| GENE_PATHWAY | 104,678 |  | ✓ | ✓ |
| GENE_PRODUCT | 19,478 | ✓ | ✓ | ✓ |
| PPI | 308,704 | ✓ | ✓ | ✓ |
| PROTEIN_GO_COMPONENT | 82,463 | ✓ | ✓ | ✓ |
| PROTEIN_GO_FUNCTION | 69,726 | ✓ | ✓ | ✓ |
| PROTEIN_GO_PROCESS | 129,189 | ✓ | ✓ | ✓ |
| PROTEIN_PATHWAY | 117,179 | ✓ | ✓ | ✓ |
| TREATS | 168,157 |  | ✓ | ✓ |

## Per-subgraph totals

### pkt_taskA_dti  — TASK A — predict DTI (chemical->protein)

- file: `dataset/PKT_subgraphs/pkt_taskA_dti.tsv.zip`
- relations: ['COMPOUND_GO', 'COMPOUND_PATHWAY', 'DTI', 'GENE_PRODUCT', 'PPI', 'PROTEIN_GO_COMPONENT', 'PROTEIN_GO_FUNCTION', 'PROTEIN_GO_PROCESS', 'PROTEIN_PATHWAY']
- **edges: 1,136,665**
- nodes per type: {'Compound': 6646, 'GO': 18881, 'Pathway': 2537, 'Protein': 19624, 'Gene': 19273}
- total nodes: 66,961

### pkt_taskB_treats  — TASK B — predict TREATS (chemical->disease)

- file: `dataset/PKT_subgraphs/pkt_taskB_treats.tsv.zip`
- relations: ['COMPOUND_GO', 'COMPOUND_PATHWAY', 'DISEASE_PHENOTYPE', 'DTI', 'GDA', 'GDA_DYSFUNCTION', 'GENE_PATHWAY', 'GENE_PRODUCT', 'PPI', 'PROTEIN_GO_COMPONENT', 'PROTEIN_GO_FUNCTION', 'PROTEIN_GO_PROCESS', 'PROTEIN_PATHWAY', 'TREATS']
- **edges: 1,853,908**
- nodes per type: {'Compound': 9453, 'GO': 18881, 'Pathway': 2537, 'Disease': 13673, 'Phenotype': 10051, 'Protein': 19624, 'Gene': 19612}
- total nodes: 93,831

### pkt_unified  — UNIFIED — both targets (multi-task)

- file: `dataset/PKT_subgraphs/pkt_unified.tsv.zip`
- relations: ['COMPOUND_GO', 'COMPOUND_PATHWAY', 'DISEASE_PHENOTYPE', 'DTI', 'GDA', 'GDA_DYSFUNCTION', 'GENE_PATHWAY', 'GENE_PRODUCT', 'PPI', 'PROTEIN_GO_COMPONENT', 'PROTEIN_GO_FUNCTION', 'PROTEIN_GO_PROCESS', 'PROTEIN_PATHWAY', 'TREATS']
- **edges: 1,853,908**
- nodes per type: {'Compound': 9453, 'GO': 18881, 'Pathway': 2537, 'Disease': 13673, 'Phenotype': 10051, 'Protein': 19624, 'Gene': 19612}
- total nodes: 93,831

