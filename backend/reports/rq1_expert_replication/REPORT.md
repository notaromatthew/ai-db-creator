# RQ1 — pannello esperto separato

## Stato del pannello

- Replica osservata separata dalle 1.350 valutazioni dei 45 trained student raters; nessun pooling.
- Il protocollo pianificava 3 esperti; il pannello osservato ne contiene 3.
- Per i primi due esperti, indipendenza, assenza di confronto/accesso ai punteggi reciproci e cecità alle condizioni sono attestazioni dell'utente, non inferenze dai dati.
- Per il terzo esperto idoneità e indipendenza sono attestate dall'utente; la cecità alle condizioni resta da confermare esplicitamente.
- L'accordo esatto osservato è 20/150 celle e 0/30 vettori-schema.

## Accordo

| Dimensione | Alpha ordinale | IC bootstrap 95% | Esatto | Adiacente |
|---|---:|---:|---:|---:|
| d1_3nf | 0.242 | [-0.030, 0.452] | 16.7% | 66.7% |
| d2_naming | -0.463 | [-0.466, -0.462] | 0.0% | 50.0% |
| d3_constraints | 0.103 | [-0.287, 0.409] | 16.7% | 66.7% |
| d4_relationships | 0.103 | [-0.296, 0.396] | 16.7% | 66.7% |
| d5_domain | 0.103 | [-0.309, 0.403] | 16.7% | 66.7% |
| overall | 0.054 | [-0.241, 0.300] | 13.3% | 63.3% |

## Confronto descrittivo fra condizioni

L'unità è lo schema (15 per condizione); i 3 giudizi sono aggregati per schema.

| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |
|---|---:|---:|---:|---:|---:|---:|
| d1_3nf | 3.644 | 4.444 | 0.800 | [0.422, 1.156] | 0.0021 | 1.515 |
| d2_naming | 4.444 | 4.533 | 0.089 | [-0.044, 0.200] | 0.2073 | 0.472 |
| d3_constraints | 4.000 | 4.533 | 0.533 | [0.178, 0.911] | 0.0670 | 0.974 |
| d4_relationships | 4.000 | 4.533 | 0.533 | [0.178, 0.911] | 0.0670 | 0.974 |
| d5_domain | 4.000 | 4.533 | 0.533 | [0.178, 0.912] | 0.0670 | 0.974 |

Il pannello raggiunge la numerosità pianificata di tre esperti, resta separato dal campione studentesco ed è attestato come indipendente. L'evidenza procedurale sulla cecità alle condizioni del terzo esperto deve essere completata prima di descrivere l'intero pannello come cieco alle condizioni.
