# TARGET candidate relations (chemical <-> gene/protein)

Coverage = distinct chemicals / distinct targets touched by the relation.

| direction | predicate_label | target_type | edges | distinct_chemicals | distinct_targets |
|---|---|---|---:|---:|---:|
| tgt->chem | type | protein | 377,333 | 17 | 55,429 |
| chem->tgt | interacts with | protein | 71,315 | 4,265 | 7,903 |
| tgt->chem | interacts with | protein | 71,315 | 4,265 | 7,903 |
| chem->tgt | molecularly interacts with | protein | 25,713 | 3,757 | 3,496 |
| tgt->chem | molecularly interacts with | protein | 25,713 | 3,757 | 3,496 |
| tgt->chem | interacts with | gene | 16,620 | 463 | 11,908 |
| chem->tgt | interacts with | gene | 16,620 | 463 | 11,908 |
| tgt->chem | has part | protein | 10,437 | 59 | 10,074 |
| chem->tgt | type | protein | 258 | 80 | 5 |
| tgt->chem | has component | protein | 71 | 3 | 67 |
| tgt->chem | derives_from | protein | 1 | 1 | 1 |
