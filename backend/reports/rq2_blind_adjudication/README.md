# RQ2 blind adjudication package

Stato: preparato, in attesa di due revisioni umane indipendenti.

## File da distribuire

- `reviewer_a.xlsx`: inviare soltanto al revisore A.
- `reviewer_b.xlsx`: inviare soltanto al revisore B.

Non distribuire `coordinator_private_mapping.xlsx`, `private_mapping.json`, i
file JSON intermedi o il manifest. Questi file rivelano condizione e run.

Ogni revisore compila tutte le 1.294 righe del foglio `Review`, selezionando
`decision` e `confidence`. Le note sono obbligatorie per `gold ambiguo` e
`non determinabile`. I revisori non devono consultarsi prima della consegna.
Non modificare `item_id`, ordinamento o colonne di evidenza.

## Procedura del coordinatore

1. conservare una copia immutata dei due file distribuiti;
2. ricevere i due file compilati separatamente;
3. verificare che i revisori attestino indipendenza e assenza di accesso a
   condizione, run, modello e punteggi;
4. eseguire l'analisi preliminare:

   ```powershell
   backend\.venv\Scripts\python.exe backend\analyze_rq2_adjudication.py `
     reviewer_a_completed.xlsx reviewer_b_completed.xlsx `
     backend\reports\rq2_blind_adjudication\private_mapping.json `
     backend\reports\rq2_adjudication_completed
   ```

5. risolvere per consenso soltanto le righe di `consensus_required.csv`, senza
   cambiare le decisioni individuali originali; il file resta cieco a
   condizione e run fino alla chiusura del consenso;
6. conservare file originali, verbale di consenso, output e hash nel pacchetto
   finale RQ2.

`manifest.json` congela selezione, semi di randomizzazione e hash dei 30 ledger
di origine. Il pacchetto include tutte le discrepanze, perché le tabelle
osservabili alimentano query critiche del protocollo RQ2.
