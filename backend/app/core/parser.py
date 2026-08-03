import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from app.utils.exceptions import ParsingException
from app.utils.logger import log


class ParsedDocument:
    def __init__(self, filename: str, text_content: str, tables: list = None, table_sources: list[str] = None):
        self.filename = filename
        self.text_content = text_content
        self.tables = tables or []
        self.table_sources = table_sources or [f"table_{index + 1}" for index in range(len(self.tables))]


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        pass


class PDFParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            return ParsedDocument(filename=Path(file_path).name, text_content=text)
        except Exception as e:
            log.warning(f"PDF parsing failed for {file_path}: {e}")
            return ParsedDocument(filename=Path(file_path).name, text_content="")


class ExcelParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        try:
            xls = pd.ExcelFile(file_path)
            all_text = []
            all_tables = []
            table_sources = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                if not df.empty:
                    all_text.append(f"[Sheet: {sheet}]\n{df.to_string()}")
                    all_tables.append([df.columns.tolist()] + df.values.astype(str).tolist())
                    table_sources.append(sheet)
            return ParsedDocument(
                filename=Path(file_path).name,
                text_content="\n\n".join(all_text),
                tables=all_tables,
                table_sources=table_sources,
            )
        except Exception as e:
            log.warning(f"Excel parsing failed for {file_path}: {e}")
            raise ParsingException(
                detail="Impossibile leggere il file Excel. Verifica che sia un file .xls/.xlsx valido e non danneggiato."
            ) from e


class TXTParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return ParsedDocument(filename=Path(file_path).name, text_content=text)
        except Exception as e:
            log.warning(f"TXT parsing failed for {file_path}: {e}")
            return ParsedDocument(filename=Path(file_path).name, text_content="")


class CSVParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252']
        delimiters = [None, ';', ',', '\t', '|']
        for enc in encodings:
            for sep in delimiters:
                try:
                    kwargs = {'filepath_or_buffer': file_path, 'encoding': enc}
                    if sep is not None:
                        kwargs['sep'] = sep
                    else:
                        kwargs['sep'] = None
                        kwargs['engine'] = 'python'
                    df = pd.read_csv(**kwargs)
                    if len(df.columns) > 0:
                        text = df.to_string()
                        table = [df.columns.tolist()] + df.values.astype(str).tolist()
                        return ParsedDocument(filename=Path(file_path).name, text_content=text, tables=[table], table_sources=["csv"])
                except:
                    continue
        log.warning(f"CSV parsing failed for {file_path} after trying all encodings/delimiters")
        return ParsedDocument(filename=Path(file_path).name, text_content="")


def get_parser(file_type: str) -> DocumentParser:
    parsers = {"pdf": PDFParser(), "xls": ExcelParser(), "xlsx": ExcelParser(), "txt": TXTParser(), "csv": CSVParser(), "sql": TXTParser()}
    return parsers.get(file_type.lower(), TXTParser())
