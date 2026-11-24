# Emendamento dei gold standard — consenso del 21 novembre 2026

## Stato

GOLD-A e GOLD-B hanno valutato indipendentemente schema, ground truth e query
attese dei dataset University, Library e Hospital. Il successivo foglio di
consenso contiene 25 decisioni finali, ciascuna con motivazione, conferma di
entrambi i valutatori e data del 21 novembre 2026.

Le schede con qualifiche, dichiarazione d'indipendenza e firma di GOLD-A e
GOLD-B sono state ricevute e verificate il 24 novembre 2026. Entrambi i
valutatori hanno confermato integralmente la dichiarazione d'indipendenza e
firmato il proprio modulo. I PDF, contenendo dati personali e firme, sono
conservati in archivio locale ad accesso ristretto e non sono pubblicati nel
repository. Il manifesto pubblico registra pseudonimi, stato, dimensioni e hash
SHA-256 senza esporre dati identificativi. La validazione procedurale dei gold
standard è pertanto completa.

Le schede sono datate 24 novembre 2026, tre giorni dopo il consenso tecnico
del 21 novembre. Sono quindi attestazioni retrospettive archiviate dopo la
revisione, non evidenza contemporanea della compilazione preventiva prevista
dal modulo. Questa deviazione temporale è conservata nel manifesto e limita
soltanto la forza della prova procedurale, non il contenuto delle 25 decisioni
di consenso già registrate.

## Provenienza

- Consenso: `backend/reports/gold_standard_consensus_20261121/Consenso_gold_standard_GOLD-A_GOLD-B.xlsx`
- SHA-256: `2bcb3fe620bcc7c2be5f7806dcda01c5fcf31083e18c889be7d6d73beb84a5a9`
- Snapshot precedente: `backend/reports/gold_standard_consensus_20261121/pre_amendment_snapshot/`
- Versione emendata: `rq2_functional_v2`
- Manifesto delle schede: `backend/reports/gold_standard_consensus_20261121/reviewer_profiles_manifest.json`

## Modifiche approvate

### University

- La PK di `enrollments` è `(student_id, course_id, semester)`.
- La chiave business documentata è email studente, codice corso e semestre;
  l'allineamento risolve le FK tramite tali identità.
- `column_alias.json` associa `courses.course_id`, non
  `enrollments.course_id`, alla colonna generata `id`.
- U09 usa `enrollments` e restituisce solo i corsi referenziati.
- Conteggi e totali delle colonne sono stati corretti.

### Library

- È stato aggiunto `loans.returned_on`, presente anche nella fonte
  denormalizzata dei prestiti.
- Le multe sono generate solo per restituzioni tardive e ogni prestito ha al
  massimo una multa.
- Gli importi usano `NUMERIC(10,2)`.
- La chiave business dei prestiti è email, data prestito e scadenza; eventuali
  duplicati indistinguibili sono confrontati come multinsieme.
- L06 dichiara esplicitamente che considera i membri con almeno un prestito.

### Hospital

- `doctors.ward_id` collega il medico al reparto; `appointments` non duplica
  più `ward_id`.
- Fonte e ground truth rispettano il mapping specialità-reparto documentato.
- H04 non confronta più `appointment_id`; usa codice fiscale, nome e specialità
  del medico e data-ora.
- H06 e H08 risolvono il reparto tramite il medico.
- È stato aggiunto `treatments.fee`. Ogni appuntamento trattato riceve una sola
  fattura pari alla somma delle tariffe più il 15%, emessa non prima
  dell'appuntamento.
- Gli importi usano `NUMERIC(10,2)` e `invoices.appointment_id` è univoco.
- Le prescrizioni sono due relazioni one-to-many e non ammettono duplicati
  esatti `(treatment_id, medication_id, dosage)`.
- `(full_name, specialty)` è univoco nella fixture; i timestamp includono i
  secondi e la tolleranza numerica è `0.005`.

## Comparabilità

L'emendamento modifica schemi, dati generati e risultati attesi. Costituisce
quindi una nuova versione degli artefatti sperimentali. I risultati v1 devono
restare etichettati come storici e non possono sostituire o essere aggregati ai
risultati v2. La nuova matrice v2 completa è stata eseguita il 21 novembre 2026
ed è archiviata in
`backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/`.
