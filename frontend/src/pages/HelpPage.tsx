import React from 'react'
import { Link } from 'react-router-dom'

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 py-4">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-8 text-white shadow-xl">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/20 text-2xl backdrop-blur">📚</span>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Guida Passo-Passo ad AI DB Creator</h1>
            <p className="mt-1 text-sm text-blue-100">
              Impara a trasformare i tuoi documenti e descrizioni in un database relazionale pronto all'uso.
            </p>
          </div>
        </div>
      </div>

      {/* Step by Step Cards */}
      <div className="space-y-6">
        {/* Step 1 */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start gap-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-100 text-lg font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
              1
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Creazione del Progetto & Scelta della Modalità</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Clicca su <strong>"Nuovo Progetto"</strong> nella Dashboard. Puoi scegliere tra due percorsi:
              </p>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-600 dark:text-slate-400">
                <li><strong>Flusso Rapido:</strong> Inserisci nome e prompt per creare direttamente la struttura.</li>
                <li><strong>Wizard Guidato:</strong> Ti accompagna passo-passo nel caricamento dei documenti e nella revisione assistita dello schema.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start gap-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-100 text-lg font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              2
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Caricamento Documenti Eterogenei</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Puoi caricare file in formato <strong>PDF, Excel (XLSX), CSV, TXT o file SQL</strong>. L'AI estrarrà sia il testo sia la struttura delle colonne per progettare le tabelle giuste.
              </p>
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start gap-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-purple-100 text-lg font-bold text-purple-700 dark:bg-purple-950 dark:text-purple-300">
              3
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Generazione & Normalizzazione 3NF dello Schema</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                L'AI progetta uno schema relazionale normalizzato in <strong>Terza Forma Normale (3NF)</strong>. Tramite l'editor visuale <em>SchemaViewer</em> puoi:
              </p>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-600 dark:text-slate-400">
                <li>Modificare i nomi delle tabelle e colonne.</li>
                <li>Aggiungere o rimuovere Primary Key (🔑) e Foreign Key (🔗).</li>
                <li>Usare la <strong>Chat Assistita</strong> per chiedere modifiche in linguaggio naturale.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Step 4 */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start gap-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-100 text-lg font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
              4
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Popolamento dei Dati & Esportazione SQL</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Clicca su <strong>"Popola Dati"</strong>. L'AI estrarrà le righe dai documenti inserendole nelle tabelle rispettando i vincoli referenziali. Successivamente puoi:
              </p>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-600 dark:text-slate-400">
                <li>Esplorare e modificare i dati via CRUD nell'interfaccia <em>DataViewer</em>.</li>
                <li>Interrogare il database in Linguaggio Naturale (es. <em>"Mostra il totale vendite per cliente"</em>).</li>
                <li>Esportare lo script DDL + INSERT pronto per <strong>SQLite, PostgreSQL, MySQL o SQL Server</strong>.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <h4 className="font-bold text-slate-900 dark:text-white">Pronto ad iniziare?</h4>
          <p className="text-xs text-slate-500">Crea il tuo primo progetto o confronta i modelli nella pagina Benchmark.</p>
        </div>
        <Link
          to="/"
          className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white shadow hover:bg-blue-700"
        >
          Torna alla Dashboard
        </Link>
      </div>
    </div>
  )
}
