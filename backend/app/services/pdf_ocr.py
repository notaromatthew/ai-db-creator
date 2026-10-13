"""Estrazione di testo da PDF scansionati con il modello multimodale gia' configurato (Vertex).

Nessuna libreria OCR: ogni pagina viene resa in immagine con PyMuPDF e inviata al modello.
Il numero di pagine e la spesa stimata per documento hanno un tetto.
"""
from dataclasses import dataclass, field
import base64

from app.utils.logger import log

OCR_PROMPT = (
    "Transcribe all the text visible on this page exactly as written, keeping the reading order. "
    "Render tables as rows with cells separated by ' | '. Output only the transcription, with no comments."
)

MAX_OCR_PAGES = 20               # tetto assoluto di pagine per documento
COST_PER_PAGE_USD = 0.002        # stima prudente per pagina (immagine in ingresso + testo in uscita)
MAX_OCR_COST_USD = 0.05          # tetto di spesa stimata per documento
RENDER_DPI = 130


@dataclass
class OcrResult:
    text: str = ""
    pages_total: int = 0
    pages_processed: int = 0
    truncated: bool = False
    estimated_cost_usd: float = 0.0
    failed_pages: list[int] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())


def multimodal_available() -> bool:
    """True se il provider configurato e' Vertex (l'unico usato per i PDF scansionati)."""
    try:
        from app.config import settings
        return settings.llm_provider == "vertex" and not settings.use_ollama
    except Exception:
        return False


def _load_model():
    """Importa solo ora il modello configurato, per non caricare Vertex finche' non serve."""
    from app.core.llm import _get_llm
    return _get_llm(temperature=0.0)


def _page_limit(max_pages: int, max_cost_usd: float) -> int:
    by_cost = int(max_cost_usd // COST_PER_PAGE_USD) if COST_PER_PAGE_USD > 0 else max_pages
    return max(0, min(max_pages, MAX_OCR_PAGES, by_cost))


def _render_pages(file_path: str, limit: int) -> tuple[list[bytes], int]:
    import fitz
    doc = fitz.open(file_path)
    try:
        total = doc.page_count
        images = [doc[i].get_pixmap(dpi=RENDER_DPI).tobytes("png") for i in range(min(total, limit))]
    finally:
        doc.close()
    return images, total


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""


def extract_text_from_pdf_with_llm(file_path: str, *, max_pages: int = MAX_OCR_PAGES,
                                   max_cost_usd: float = MAX_OCR_COST_USD, model=None) -> OcrResult:
    """Legge un PDF pagina per pagina con il modello multimodale e restituisce il testo trascritto.

    `model` serve ai test: deve avere `invoke(messages)` e restituire un oggetto con `content`.
    Un errore su una pagina non ferma le altre; non si scrivono mai testo o contenuti nei log.
    """
    limit = _page_limit(max_pages, max_cost_usd)
    images, total = _render_pages(file_path, limit)
    result = OcrResult(pages_total=total, truncated=total > len(images))
    if not images:
        return result
    llm = model if model is not None else _load_model()
    from langchain_core.messages import HumanMessage

    texts = []
    for index, png in enumerate(images, start=1):
        message = HumanMessage(content=[
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}},
        ])
        result.estimated_cost_usd = round(result.estimated_cost_usd + COST_PER_PAGE_USD, 6)
        result.pages_processed += 1
        try:
            reply = llm.invoke([message])
        except Exception as exc:
            log.warning(f"OCR pagina {index} non riuscito ({type(exc).__name__})")
            result.failed_pages.append(index)
            continue
        page_text = _content_to_text(getattr(reply, "content", "")).strip()
        if page_text:
            texts.append(f"[Pagina {index}]\n{page_text}")
    result.text = "\n\n".join(texts)
    return result
