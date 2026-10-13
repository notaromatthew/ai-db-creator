import type { Document } from '@/types'

/** Avviso sui documenti che sembrano scansioni, senza testo selezionabile. */
export default function OcrNotice({ documents }: { documents: Pick<Document, 'id' | 'filename' | 'needs_ocr'>[] }) {
  const scans = documents.filter((d) => d.needs_ocr)
  if (scans.length === 0) return null
  return (
    <div role="note" className="flex items-start gap-2 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">document_scanner</span>
      <p>
        {scans.length === 1 ? 'Questo file sembra una scansione' : 'Questi file sembrano scansioni'}: {scans.map((d) => d.filename).join(', ')}.
        Il testo va riconosciuto con l'IA (OCR) e conta come una richiesta in più.
      </p>
    </div>
  )
}
