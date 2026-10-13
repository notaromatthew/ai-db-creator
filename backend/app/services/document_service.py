from app.core.parser import get_parser
from app.models.database import Document, get_session, init_db
from app.utils.exceptions import AppException
from app.utils.logger import log
from pathlib import Path
import shutil
import uuid

UPLOAD_DIR = "uploads"
OCR_SIDECAR_SUFFIX = ".ocr.txt"


def load_ocr_text(file_path: str) -> str:
    """Testo ottenuto con OCR per un PDF scansionato (salvato accanto al file), oppure stringa vuota."""
    sidecar = Path(str(file_path) + OCR_SIDECAR_SUFFIX)
    try:
        return sidecar.read_text(encoding="utf-8") if sidecar.exists() else ""
    except OSError:
        return ""


class DocumentService:
    def __init__(self):
        self.engine = init_db()
    
    def upload_document(self, project_id: str, file_path: str, original_filename: str = None,
                        ocr_gate=None) -> Document:
        """Salva il documento. `ocr_gate` (opzionale) e' chiamata prima di usare il modello per un PDF scansionato
        e restituisce False se l'OCR non e' consentito (per esempio quota esaurita)."""
        fp = Path(file_path)
        ft = fp.suffix.lower().lstrip(".")
        parser = get_parser(ft)
        parsed = parser.parse(str(fp))
        # Il nome originale resta nei metadati per la UI; su disco ogni upload
        # ha un nome indipendente per non sovrascrivere file omonimi.
        safe_name = Path(original_filename or fp.name).name
        storage_name = f"{uuid.uuid4().hex}{fp.suffix.lower()}"
        dest = Path(UPLOAD_DIR) / project_id / storage_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(fp), str(dest))

        summary = parsed.text_content
        needs_ocr = ft == "pdf" and not summary.strip()
        if needs_ocr:
            summary = self._try_ocr(dest, ocr_gate)
            needs_ocr = not summary.strip()

        session = get_session(self.engine)
        doc = Document(project_id=project_id, filename=safe_name, file_type=ft, file_path=str(dest),
                       content_summary=summary[:5000], needs_ocr=needs_ocr)
        session.add(doc)
        session.commit()
        doc_id = doc.id
        session.close()
        return self.get_document(doc_id, project_id)
    
    def _try_ocr(self, dest: Path, ocr_gate) -> str:
        """OCR con il modello multimodale, se disponibile e consentito. Il testo completo va in un file accanto."""
        from app.services import pdf_ocr
        if not pdf_ocr.multimodal_available():
            return ""
        if ocr_gate is not None and not ocr_gate():
            return ""
        try:
            outcome = pdf_ocr.extract_text_from_pdf_with_llm(str(dest))
        except Exception as exc:
            log.warning(f"OCR del PDF non riuscito ({type(exc).__name__})")
            return ""
        if outcome.ok:
            Path(str(dest) + OCR_SIDECAR_SUFFIX).write_text(outcome.text, encoding="utf-8")
            log.info(f"OCR completato: {outcome.pages_processed}/{outcome.pages_total} pagine")
        return outcome.text

    def get_document(self, doc_id: str, project_id: str | None = None) -> Document:
        session = get_session(self.engine)
        query = session.query(Document).filter(Document.id == doc_id)
        if project_id is not None:
            query = query.filter(Document.project_id == project_id)
        doc = query.first()
        session.close()
        if not doc:
            raise AppException(detail="Document not found", status_code=404)
        return doc
    
    def list_documents(self, project_id: str) -> list:
        session = get_session(self.engine)
        docs = session.query(Document).filter(Document.project_id == project_id).all()
        session.close()
        return docs

    def delete_document(self, project_id: str, doc_id: str):
        session = get_session(self.engine)
        doc = session.query(Document).filter(Document.id == doc_id, Document.project_id == project_id).first()
        if not doc:
            session.close()
            raise AppException(detail="Document not found", status_code=404)
        fp = Path(doc.file_path)
        try:
            if fp.exists():
                fp.unlink()
            sidecar = Path(str(fp) + OCR_SIDECAR_SUFFIX)
            if sidecar.exists():
                sidecar.unlink()
        except Exception as e:
            log.warning(f"Could not delete file {fp}: {e}")
        session.delete(doc)
        session.commit()
        session.close()
        return {"deleted": doc_id}
