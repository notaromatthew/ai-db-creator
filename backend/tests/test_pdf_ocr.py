import asyncio
from types import SimpleNamespace

import fitz
import pytest

from app.models.database import Document, get_session
from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef
from app.services import pdf_ocr, population_service
from app.services.document_service import DocumentService, OCR_SIDECAR_SUFFIX, load_ocr_text
from app.services.pdf_ocr import OcrResult, extract_text_from_pdf_with_llm
from app.services.population_service import PopulationService


def scanned_pdf(path, pages=2):
    """PDF con pagine solo grafiche: nessun testo estraibile."""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.draw_rect(fitz.Rect(50, 50, 300, 200), fill=(0.8, 0.8, 0.8))
    doc.save(str(path))
    doc.close()
    return path


class FakeModel:
    def __init__(self, fail_on=()):
        self.calls = []
        self.fail_on = set(fail_on)

    def invoke(self, messages):
        index = len(self.calls) + 1
        self.calls.append(messages)
        if index in self.fail_on:
            raise RuntimeError("errore del modello")
        content = messages[0].content
        assert content[0]["type"] == "text" and content[1]["image_url"]["url"].startswith("data:image/png;base64,")
        return SimpleNamespace(content=f"Testo della pagina {index}")


def test_text_is_extracted_page_by_page(tmp_path):
    path = scanned_pdf(tmp_path / "scan.pdf", pages=3)
    model = FakeModel()
    result = extract_text_from_pdf_with_llm(str(path), model=model)
    assert len(model.calls) == 3
    assert result.pages_total == 3 and result.pages_processed == 3 and not result.truncated
    assert "[Pagina 1]\nTesto della pagina 1" in result.text and "Testo della pagina 3" in result.text
    assert result.ok


def test_page_cap_is_twenty(tmp_path):
    path = scanned_pdf(tmp_path / "lungo.pdf", pages=25)
    model = FakeModel()
    result = extract_text_from_pdf_with_llm(str(path), model=model, max_pages=100, max_cost_usd=100)
    assert len(model.calls) == 20 == pdf_ocr.MAX_OCR_PAGES
    assert result.pages_total == 25 and result.truncated


def test_cost_cap_limits_pages(tmp_path):
    path = scanned_pdf(tmp_path / "costo.pdf", pages=10)
    model = FakeModel()
    result = extract_text_from_pdf_with_llm(str(path), model=model, max_cost_usd=pdf_ocr.COST_PER_PAGE_USD * 3)
    assert len(model.calls) == 3 and result.truncated
    assert result.estimated_cost_usd == pytest.approx(pdf_ocr.COST_PER_PAGE_USD * 3)


def test_zero_budget_does_not_call_the_model(tmp_path):
    path = scanned_pdf(tmp_path / "zero.pdf")
    model = FakeModel()
    result = extract_text_from_pdf_with_llm(str(path), model=model, max_cost_usd=0)
    assert model.calls == [] and result.text == "" and not result.ok


def test_a_failing_page_does_not_stop_the_others(tmp_path):
    path = scanned_pdf(tmp_path / "scan.pdf", pages=3)
    result = extract_text_from_pdf_with_llm(str(path), model=FakeModel(fail_on={2}))
    assert result.failed_pages == [2]
    assert "pagina 1" in result.text and "pagina 3" in result.text and "[Pagina 2]" not in result.text


def test_list_content_from_the_model_is_flattened(tmp_path):
    class ListModel:
        def invoke(self, messages):
            return SimpleNamespace(content=[{"type": "text", "text": "Ciao "}, {"type": "text", "text": "mondo"}])

    result = extract_text_from_pdf_with_llm(str(scanned_pdf(tmp_path / "a.pdf", pages=1)), model=ListModel())
    assert "Ciao mondo" in result.text


def test_multimodal_available_only_for_vertex(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "llm_provider", "vertex")
    assert pdf_ocr.multimodal_available()
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert not pdf_ocr.multimodal_available()


def upload(service, path, **kwargs):
    return service.upload_document("p1", str(path), original_filename="scan.pdf", **kwargs)


def test_scanned_pdf_without_provider_is_marked_needs_ocr(client, tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: False)
    service = DocumentService()
    doc = upload(service, scanned_pdf(tmp_path / "scan.pdf"))
    assert doc.needs_ocr is True and doc.content_summary == ""


def test_scanned_pdf_with_provider_is_read_and_saved(client, tmp_path, monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "_load_model", lambda: model)
    service = DocumentService()
    doc = upload(service, scanned_pdf(tmp_path / "scan.pdf"))
    assert doc.needs_ocr is False
    assert "Testo della pagina 1" in doc.content_summary
    assert "Testo della pagina 2" in load_ocr_text(doc.file_path)
    service.delete_document("p1", doc.id)
    import os
    assert not os.path.exists(doc.file_path + OCR_SIDECAR_SUFFIX)


def test_ocr_gate_can_refuse(client, tmp_path, monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "_load_model", lambda: model)
    doc = upload(DocumentService(), scanned_pdf(tmp_path / "scan.pdf"), ocr_gate=lambda: False)
    assert doc.needs_ocr is True and model.calls == []


def test_ocr_failure_leaves_needs_ocr(client, tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("credenziali scadute")

    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "extract_text_from_pdf_with_llm", explode)
    doc = upload(DocumentService(), scanned_pdf(tmp_path / "scan.pdf"))
    assert doc.needs_ocr is True


def test_pdf_with_text_does_not_need_ocr(client, tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "_load_model", lambda: pytest.fail("OCR non necessario"))
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Fattura numero 42")
    path = tmp_path / "testo.pdf"
    pdf.save(str(path)); pdf.close()
    doc = upload(DocumentService(), path)
    assert doc.needs_ocr is False and "Fattura numero 42" in doc.content_summary


def test_upload_endpoint_reports_needs_ocr_and_consumes_quota(client, project, tmp_path, monkeypatch):
    c, _ = client
    pid = project["id"]
    from app.core.quota import count_today
    model = FakeModel()
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "_load_model", lambda: model)
    data = scanned_pdf(tmp_path / "s.pdf").read_bytes()
    before = count_today("test-user")
    response = c.post(f"/api/projects/{pid}/documents", files={"file": ("s.pdf", data, "application/pdf")})
    assert response.status_code == 200 and response.json()["needs_ocr"] is False
    assert count_today("test-user") == before + 1
    listed = c.get(f"/api/projects/{pid}/documents").json()
    assert listed[0]["needs_ocr"] is False


def test_population_uses_the_saved_ocr_text(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pdf_ocr, "multimodal_available", lambda: True)
    monkeypatch.setattr(pdf_ocr, "_load_model", lambda: FakeModel())
    service = DocumentService()
    doc = upload(service, scanned_pdf(tmp_path / "scan.pdf"))
    schema = NormalizedSchema(tables=[TableDef(name="persone", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True), ColumnDef(name="nome", data_type="TEXT")])],
        relationships=[])
    seen = {}

    async def sql(_schema, content, temperature=None):
        seen["content"] = content
        return "INSERT INTO persone (id, nome) VALUES (1, 'Ada');"

    monkeypatch.setattr(population_service, "generate_sql_for_population", sql)
    result = asyncio.run(PopulationService().populate("p1", str(tmp_path / "database.sqlite"), schema, [doc.id]))
    assert "Testo della pagina 1" in seen["content"]
    assert result["persone"]["inserted"] == 1
