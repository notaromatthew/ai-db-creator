# RQ0/RQ3 analysis of available completed records

The analysis is based on the available completed records.

## Included records

The analysis includes 102 valid cases, with 34 cases in each arm.

## Descriptive results

| Arm | N | Schema quality, mean (SD) | Residual error, mean (SD) | Duration min, mean (SD) | Task success |
|---|---:|---:|---:|---:|---:|
| manual | 34 | 4.971 (0.171) | 1.971% (0.706%) | 39.94 (1.41) | 34/34 |
| ai_only | 34 | 4.971 (0.171) | 1.985% (0.723%) | 28.56 (1.13) | 34/34 |
| ai_interface | 34 | 5.000 (0.000) | 2.000% (0.728%) | 26.44 (1.13) | 34/34 |

## Contrasts

| RQ | Contrast | Outcome | Mean difference | Cohen d (95% bootstrap CI) | Welch p | Holm p |
|---|---|---|---:|---:|---:|---:|
| RQ0 | manual - ai_interface | schema_quality | -0.0294 | -0.243 [-0.433, 0.000] | 0.3246 | 1.0000 |
| RQ0 | manual - ai_interface | residual_error_rate | -0.0003 | -0.041 [-0.531, 0.429] | 0.8663 | 1.0000 |
| RQ0 | manual - ai_interface | duration_minutes | 13.5000 | 10.541 [9.624, 12.149] | 1.052e-48 | — |
| RQ3 | ai_only - ai_interface | schema_quality | -0.0294 | -0.243 [-0.433, 0.000] | 0.3246 | 1.0000 |
| RQ3 | ai_only - ai_interface | residual_error_rate | -0.0001 | -0.020 [-0.491, 0.458] | 0.9337 | 1.0000 |
| RQ3 | ai_only - ai_interface | duration_minutes | 2.1176 | 1.869 [1.401, 2.481] | 8.951e-11 | — |

## Blind-rating agreement

The two ratings agree exactly in 86/102 cases (84.3%).

## Interpretation

Neither preregistered primary outcome differs after Holm correction. AI + Interface is faster than both Manual and AI-Only on the secondary duration outcome. Task success is 100% in every arm.
