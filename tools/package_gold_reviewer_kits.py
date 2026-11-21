from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "gold_standard_validation"
DATASETS = ROOT / "data" / "datasets"


README = """AI-DB-Creator - Kit di validazione indipendente dei gold standard

Valutatore: {code}

Contenuto
- Scheda_valutatore_{code}.docx: profilo, esperienza, indipendenza, data e firma.
- Valutazione_gold_standard_{code}.xlsx: istruzioni e moduli per schema, dati e query.
- Protocollo/: criteri scientifici da applicare.
- Datasets/: fonti, schema gold, database ground truth, specifica di valutazione e script di costruzione.
- MANIFEST_SHA256.txt: impronte dei file inclusi.

Procedura
1. Compilare e firmare la scheda DOCX.
2. Aprire il file XLSX e leggere per intero il foglio Istruzioni.
3. Compilare il foglio Profilo.
4. Valutare University, Library e Hospital usando esclusivamente i materiali del kit.
5. Valutare tutte le query del foglio Query.
6. Per MODIFICA o INCERTO indicare gravita, correzione proposta e motivazione/evidenza.
7. Controllare il foglio Riepilogo e risolvere tutti i campi DA COMPLETARE.
8. Restituire DOCX e XLSX senza confrontarsi con l'altro valutatore.

La fase di consenso iniziera soltanto dopo la consegna indipendente di GOLD-A e GOLD-B.
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add_file(files: list[tuple[str, bytes]], arcname: str, source: Path) -> None:
    files.append((arcname.replace("\\", "/"), source.read_bytes()))


def build(code: str) -> Path:
    files: list[tuple[str, bytes]] = []
    files.append(("LEGGIMI.txt", README.format(code=code).encode("utf-8")))
    add_file(files, f"Scheda_valutatore_{code}.docx", OUTPUT / f"Scheda_valutatore_{code}.docx")
    add_file(files, f"Valutazione_gold_standard_{code}.xlsx", OUTPUT / f"Valutazione_gold_standard_{code}.xlsx")
    add_file(files, "Protocollo/11-benchmark-protocol.md", ROOT / "docs" / "11-benchmark-protocol.md")
    add_file(
        files,
        "Protocollo/20-rq2-functional-equivalence-protocol.md",
        ROOT / "docs" / "20-rq2-functional-equivalence-protocol.md",
    )
    for dataset in ("university", "library", "hospital"):
        base = DATASETS / dataset
        for source in sorted(base.rglob("*")):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            relative = source.relative_to(base).as_posix()
            add_file(files, f"Datasets/{dataset}/{relative}", source)

    manifest_lines = [f"{sha256(data)}  {name}" for name, data in sorted(files)]
    manifest = ("\n".join(manifest_lines) + "\n").encode("utf-8")
    files.append(("MANIFEST_SHA256.txt", manifest))

    zip_path = OUTPUT / f"Kit_validazione_gold_standard_{code}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in files:
            archive.writestr(name, data)
    return zip_path


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for code in ("GOLD-A", "GOLD-B"):
        print(build(code))


if __name__ == "__main__":
    main()
