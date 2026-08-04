from app.models.schema_models import NormalizedSchema, TableDef
from app.models.database import get_session, init_db, Document
from app.core.parser import get_parser
from app.core.llm import generate_data_for_table, map_columns_to_tables, generate_sql_for_population
from app.core.db_generator import create_database_from_schema
from app.utils.exceptions import AppException
from app.utils.logger import log
from app.utils.research import sha256_file, stable_hash
from app.core.sql_importer import split_sql_statements
from sqlalchemy import create_engine, inspect, text
import re

MAX_LLM_DOCUMENT_CHARS = 5000


def _llm_document_text(document, text_value: str, warnings: list[dict]) -> str:
    if len(text_value) > MAX_LLM_DOCUMENT_CHARS:
        warnings.append({"category": "llm_input_truncated", "document_id": document.id,
                         "document_hash": sha256_file(document.file_path),
                         "original_chars": len(text_value), "used_chars": MAX_LLM_DOCUMENT_CHARS})
    return text_value[:MAX_LLM_DOCUMENT_CHARS]


def _has_single_values_tuple(statement: str) -> bool:
    match = re.search(r"\bVALUES\b(.*)$", statement, re.IGNORECASE | re.DOTALL)
    if not match:
        return False
    value_sql = match.group(1).strip()
    depth = 0
    tuple_count = 0
    quote = None
    index = 0
    while index < len(value_sql):
        char = value_sql[index]
        if quote:
            if char == quote:
                if index + 1 < len(value_sql) and value_sql[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            if depth == 0:
                tuple_count += 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
        index += 1
    return tuple_count == 1 and depth == 0 and quote is None

def _normalize_col(name: str) -> str:
    name = name.lower().strip()
    name = name.replace(" ", "_").replace("'", "").replace('"', "")
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_(di|del|della|degli|dei|dal|dallo|dai|dall|da)_", "_", name)
    name = re.sub(r"^_(di|del|della|degli|dei|dal|dallo|dai|dall|da)_", "", name)
    name = name.strip("_")
    return name

class PopulationService:
    def __init__(self):
        self.engine = init_db()

    def _find_table_def(self, schema: NormalizedSchema, table_name: str) -> TableDef | None:
        for t in schema.tables:
            if t.name == table_name:
                return t
        return None

    def _get_pk_columns(self, table_def: TableDef) -> list[str]:
        return [c.name for c in table_def.columns if c.is_primary_key]

    def _auto_match_columns(self, header_norm: list[str], table_def: TableDef) -> dict[int, str]:
        col_map = {}
        for i, hn in enumerate(header_norm):
            for tc in table_def.columns:
                target_name = _normalize_col(tc.name)
                if hn == target_name:
                    col_map[i] = tc.name
                    break
            if i not in col_map:
                for tc in table_def.columns:
                    target_name = _normalize_col(tc.name)
                    if hn and target_name and (hn in target_name or target_name in hn):
                        col_map[i] = tc.name
                        break
        return col_map

    def _extract_rows(self, pt: list, header_norm: list[str], col_map: dict[int, str]) -> list[dict]:
        rows = []
        for data_row in pt[1:]:
            rd = {}
            for i in range(min(len(header_norm), len(data_row))):
                dst = col_map.get(i)
                if dst:
                    val = str(data_row[i]) if data_row[i] is not None else None
                    if val and val.lower() in ("nan", "null", "none", ""):
                        val = None
                    rd[dst] = val
            if any(v is not None for v in rd.values()):
                rows.append(rd)
        return rows

    def _add_fk_references(self, llm_mapping: dict, schema: NormalizedSchema):
        for rel in schema.relationships:
            for src_tn, src_cm in list(llm_mapping.items()):
                for idx, col_name in src_cm.items():
                    if col_name == rel.from_column and src_tn == rel.from_table:
                        other_tn = rel.to_table
                        if other_tn not in llm_mapping:
                            llm_mapping[other_tn] = {}
                        if idx not in llm_mapping[other_tn]:
                            llm_mapping[other_tn][idx] = rel.to_column
                    elif col_name == rel.to_column and src_tn == rel.to_table:
                        other_tn = rel.from_table
                        if other_tn not in llm_mapping:
                            llm_mapping[other_tn] = {}
                        if idx not in llm_mapping[other_tn]:
                            llm_mapping[other_tn][idx] = rel.from_column

    async def populate(self, project_id, db_path, schema, document_ids,
                       temperature: float | None = None):
        # Validate the complete ownership set before touching the target database
        # or its parent directory. A 404 must be side-effect free.
        session = get_session(self.engine)
        try:
            docs = session.query(Document).filter(
                Document.id.in_(document_ids), Document.project_id == project_id
            ).all() if document_ids else []
        finally:
            session.close()
        if len(docs) != len(set(document_ids)):
            raise AppException(detail="Document not found", status_code=404)

        # Ensure the database is a fresh SQLite file with the correct schema
        import os
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)

        db_engine = create_engine("sqlite:///" + db_path)
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()

        if tables:
            with db_engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys = OFF;"))
                for t in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS [{t}]"))
                conn.commit()
                conn.execute(text("PRAGMA foreign_keys = ON;"))
            log.info(f"Dropped {len(tables)} existing tables from {db_path}")

        create_database_from_schema(schema, db_path)
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        log.info(f"Created {len(tables)} tables in {db_path}")
        all_docs_text = ""
        pipeline_warnings = []
        parsed_documents = {}
        llm_text_by_document = {}

        for doc in docs:
            parser = get_parser(doc.file_type)
            try:
                parsed = parser.parse(doc.file_path)
                parsed_documents[doc.id] = parsed
            except Exception as exc:
                pipeline_warnings.append({"category": "parser_error", "document_id": doc.id,
                                          "document_hash": sha256_file(doc.file_path),
                                          "error_type": type(exc).__name__})
                continue
            if not parsed.tables and not parsed.text_content.strip():
                pipeline_warnings.append({"category": "parser_empty", "document_id": doc.id,
                                          "document_hash": sha256_file(doc.file_path)})
            all_docs_text += f"\n--- DOCUMENT: {doc.filename} ({doc.file_type}) ---\n"
            if parsed.tables:
                for idx, tbl in enumerate(parsed.tables):
                    all_docs_text += f"\n[Table #{idx + 1}]\n"
                    for row in tbl:
                        all_docs_text += " | ".join(str(v) for v in row) + "\n"
            if parsed.text_content:
                llm_text_by_document[doc.id] = _llm_document_text(doc, parsed.text_content, pipeline_warnings)
                all_docs_text += f"\n[Text Content]\n{llm_text_by_document[doc.id]}\n"

        # The full-LLM path is the primary population route for every document
        # type (structured and unstructured). It receives the complete document
        # content and decides how to map values into the schema, dropping only
        # rows that are already present in the target tables. The deterministic
        # mapper below is retained strictly as a fallback when the LLM returns
        # no usable SQL or no documents were provided.
        if all_docs_text.strip():
            log.info(f"Generating population SQL via LLM for project {project_id}...")
            sql_script = await generate_sql_for_population(schema, all_docs_text,
                                                            temperature=temperature)
            if sql_script.strip():
                clean_sql = re.sub(r'```\w*', '', sql_script).replace('```', '').strip()
                statements = split_sql_statements(clean_sql)
                results = {tn: {"inserted": 0, "skipped": 0, "failed": 0, "warnings": [], "provenance": {
                    "method": "llm", "confidence": None, "document_ids": document_ids, "rows": []
                }} for tn in tables}
                for result in results.values():
                    result["warnings"].extend(pipeline_warnings)
                log.info(f"Executing {len(statements)} LLM-generated SQL statements...")

                with db_engine.connect() as conn:
                    conn.execute(text("PRAGMA foreign_keys = OFF;"))
                    for stmt in statements:
                        match = re.match(r"INSERT(?:\s+OR\s+IGNORE)?\s+INTO\s+[\[\"`]?([^\]\"`\s(]+)[\]\"`]?\s*\(([^)]+)\)", stmt, re.IGNORECASE)
                        table_name = match.group(1) if match else "unknown"
                        columns = [item.strip().strip("[]\"`") for item in match.group(2).split(",")] if match else []
                        table_result = results.setdefault(table_name, {"inserted": 0, "skipped": 0, "failed": 0,
                            "warnings": [], "provenance": {"method": "llm", "confidence": None,
                            "document_ids": document_ids, "rows": []}})
                        trace = {"source_documents": [{"document_id": doc.id, "filename": doc.filename} for doc in docs],
                                 "target_table": table_name, "target_columns": [
                                     {"target_column": column, "source_coordinate": "unstructured_text"} for column in columns
                                 ]}
                        if not _has_single_values_tuple(stmt):
                            table_result["failed"] += 1
                            table_result["warnings"].append({"category": "multi_row_or_unsupported_insert"})
                            table_result["provenance"]["rows"].append({
                                **trace, "outcome": "failed", "reason": "multi_row_or_unsupported_insert"
                            })
                            continue
                        try:
                            execution = conn.execute(text(stmt))
                            if execution.rowcount and execution.rowcount > 0:
                                table_result["inserted"] += execution.rowcount
                                table_def = self._find_table_def(schema, table_name)
                                pk_columns = self._get_pk_columns(table_def) if table_def else []
                                pk_values = []
                                if execution.lastrowid is not None and pk_columns:
                                    try:
                                        materialized = conn.execute(text(
                                            f"SELECT {', '.join(f'[{pk}]' for pk in pk_columns)} FROM [{table_name}] WHERE rowid = :rowid"
                                        ), {"rowid": execution.lastrowid}).first()
                                        pk_values = list(materialized) if materialized else []
                                    except Exception:
                                        pk_values = []
                                identity_method = "primary_key" if pk_values and all(value is not None for value in pk_values) else "lastrowid_fallback"
                                identity_values = pk_values if identity_method == "primary_key" else [execution.lastrowid]
                                table_result["provenance"]["rows"].append({**trace, "outcome": "inserted",
                                    "identity_method": identity_method,
                                    "target_row_key": stable_hash(tuple(str(value) for value in identity_values))})
                            else:
                                table_result["skipped"] += 1
                                table_result["provenance"]["rows"].append({**trace, "outcome": "skipped", "reason": "database_ignored"})
                        except Exception as exc:
                            log.warning(f"LLM population statement failed ({type(exc).__name__})")
                            table_result["failed"] += 1
                            table_result["warnings"].append({"category": "statement_execution_error", "error_type": type(exc).__name__})
                            table_result["provenance"]["rows"].append({**trace, "outcome": "failed", "reason": "statement_execution_error"})
                    conn.commit()
                    conn.execute(text("PRAGMA foreign_keys = ON;"))
                return results
            pipeline_warnings.append({"category": "fallback_sql_empty"})

        unstructured_text = ""
        structured_rows = {}
        table_provenance = {}

        for doc in docs:
            parsed = parsed_documents.get(doc.id)
            if parsed is None:
                continue
            for table_index, pt in enumerate(parsed.tables):
                if len(pt) > 1:
                    raw_header = [str(h) for h in pt[0]]
                    header_norm = [_normalize_col(h) for h in raw_header]

                    deterministic_mapping = {}
                    mapped_indices = set()
                    for table_def in schema.tables:
                        auto_map = self._auto_match_columns(header_norm, table_def)
                        if auto_map:
                            deterministic_mapping[table_def.name] = auto_map
                            mapped_indices.update(auto_map.keys())

                    # Semantic mapping is used only for columns the deterministic
                    # matcher could not confidently associate with the schema.
                    needs_semantic_mapping = len(mapped_indices) < len(raw_header)
                    semantic_mapping = await map_columns_to_tables(
                        raw_header, pt[1:], schema.tables, schema.relationships
                    ) if needs_semantic_mapping else {}
                    if needs_semantic_mapping and not semantic_mapping:
                        pipeline_warnings.append({"category": "semantic_mapping_empty", "document_id": doc.id,
                                                  "table_index": table_index})
                    llm_mapping = {name: dict(mapping) for name, mapping in semantic_mapping.items()}
                    for table_name, column_map in deterministic_mapping.items():
                        llm_mapping.setdefault(table_name, {}).update(column_map)

                    if llm_mapping:
                        self._add_fk_references(llm_mapping, schema)

                    for tn in tables:
                        tdef = self._find_table_def(schema, tn)
                        if not tdef:
                            continue

                        col_map = None
                        if llm_mapping and tn in llm_mapping:
                            col_map = llm_mapping[tn]
                        else:
                            tcols = {c.name for c in tdef.columns}
                            if not any(h in tcols for h in header_norm):
                                continue
                            auto_map = self._auto_match_columns(header_norm, tdef)
                            if auto_map:
                                col_map = auto_map

                        if not col_map:
                            continue

                        if tn not in structured_rows:
                            structured_rows[tn] = []
                        extracted_rows = self._extract_rows(pt, header_norm, col_map)
                        deterministic_columns = deterministic_mapping.get(tn, {})
                        semantic_columns = semantic_mapping.get(tn, {})
                        used_semantic = any(index in semantic_columns for index in col_map)
                        provenance = table_provenance.setdefault(tn, {
                            "method": "deterministic", "confidence": None,
                            "document_ids": [], "sources": [], "mappings": [], "rows": [],
                        })
                        if doc.id not in provenance["document_ids"]:
                            provenance["document_ids"].append(doc.id)
                        if used_semantic:
                            provenance["method"] = "hybrid"
                        source_table = parsed.table_sources[table_index] if table_index < len(parsed.table_sources) else f"table_{table_index + 1}"
                        provenance["sources"].append({
                            "document_id": doc.id, "filename": doc.filename,
                            "source_table": source_table, "table_index": table_index,
                        })
                        for source_column, target_column in col_map.items():
                            provenance["mappings"].append({
                                "document_id": doc.id, "table_index": table_index,
                                "source_table": source_table, "source_header": raw_header[source_column],
                                "source_column_index": source_column, "target_table": tn,
                                "target_column": target_column,
                                "mapping_method": (
                                    "deterministic" if source_column in deterministic_columns
                                    else "llm_semantic" if source_column in semantic_columns
                                    else "relationship_inference"
                                ),
                            })
                        extracted_index = 0
                        for source_row_index in range(1, len(pt)):
                            source_row = pt[source_row_index]
                            if not any(
                                column_index < len(source_row)
                                and str(source_row[column_index]).strip().lower() not in ("", "nan", "none", "null")
                                for column_index in col_map
                            ):
                                continue
                            if extracted_index >= len(extracted_rows):
                                continue
                            structured_rows[tn].append({"values": extracted_rows[extracted_index], "source": {
                                "document_id": doc.id, "table_index": table_index,
                                "source_table": source_table, "source_row_index": source_row_index,
                                "target_columns": [
                                    {"target_column": target_column, "source_column_index": source_column,
                                     "source_header": raw_header[source_column]}
                                    for source_column, target_column in col_map.items()
                                ],
                            }})
                            extracted_index += 1

            if parsed.text_content.strip():
                unstructured_text += f"\n--- Document: {doc.filename} ---\n{llm_text_by_document.get(doc.id, '')}"

        results = {}
        with db_engine.connect() as conn:
            for table_name in tables:
                cols_info = inspector.get_columns(table_name)
                col_names = [c["name"] for c in cols_info]
                table_def = self._find_table_def(schema, table_name)
                pk_cols = self._get_pk_columns(table_def) if table_def else []

                candidates = structured_rows.get(table_name, [])

                if table_def and not candidates and unstructured_text.strip():
                    llm_rows = await generate_data_for_table(table_def, unstructured_text)
                    if not llm_rows:
                        pipeline_warnings.append({"category": "llm_extraction_empty", "target_table": table_def.name})
                    for r in llm_rows:
                        row = {c: r.get(c, r.get(c.lower(), None)) for c in col_names}
                        if any(v is not None for v in row.values()):
                            candidates.append({"values": row, "source": None})

                if candidates:
                    pk_list_str = ", ".join(f"[{pk}]" for pk in pk_cols) if pk_cols else ""

                    has_pk_values = False
                    if pk_cols:
                        for candidate in candidates[:50]:
                            rd = candidate["values"]
                            if any(rd.get(pk, None) not in (None, "", "None", "null", "nan") for pk in pk_cols):
                                has_pk_values = True
                                break

                    existing_hashes = set()
                    if has_pk_values:
                        try:
                            existing = conn.execute(text(f"SELECT DISTINCT {pk_list_str} FROM [{table_name}]")).fetchall()
                            existing_hashes = {tuple(str(v) for v in row) for row in existing}
                        except:
                            pass
                    else:
                        non_pk = [c for c in col_names if c not in pk_cols]
                        if non_pk:
                            try:
                                non_pk_str = ", ".join(f"[{c}]" for c in non_pk)
                                existing = conn.execute(text(f"SELECT DISTINCT {non_pk_str} FROM [{table_name}]")).fetchall()
                                existing_hashes = {tuple(str(v) for v in row) for row in existing}
                            except:
                                pass

                    col_list = ", ".join(f"[{c}]" for c in col_names)
                    param_list = ", ".join(f":{c}" for c in col_names)
                    sql = f"INSERT INTO [{table_name}] ({col_list}) VALUES ({param_list})"
                    inserted = 0
                    skipped = 0
                    failed = 0
                    provenance = table_provenance.get(table_name)
                    if not provenance and unstructured_text.strip():
                        provenance = {"method": "llm", "confidence": None, "document_ids": document_ids,
                                      "sources": [], "mappings": [], "rows": []}
                    if provenance is not None:
                        provenance["rows"] = []
                    for candidate in candidates:
                        rd = candidate["values"]
                        params = {c: rd.get(c, None) for c in col_names}
                        source = candidate.get("source")
                        trace = {**(source or {}), "target_table": table_name}
                        if all(v is None for v in params.values()):
                            skipped += 1
                            if provenance is not None:
                                provenance["rows"].append({**trace, "outcome": "skipped", "reason": "empty_row"})
                            continue

                        if has_pk_values and pk_cols:
                            row_key = tuple(str(params.get(pk, "")) for pk in pk_cols)
                        else:
                            non_pk = [c for c in col_names if c not in pk_cols]
                            row_key = tuple(str(params.get(c, "")) for c in non_pk)
                        if row_key in existing_hashes:
                            skipped += 1
                            if provenance is not None:
                                provenance["rows"].append({**trace, "outcome": "skipped", "reason": "duplicate"})
                            continue

                        try:
                            execution = conn.execute(text(sql), params)
                            if execution.rowcount and execution.rowcount > 0:
                                inserted += 1
                                if provenance is not None:
                                    materialized_pk = [params.get(pk) for pk in pk_cols]
                                    if len(pk_cols) == 1 and materialized_pk[0] in (None, "") and execution.lastrowid is not None:
                                        materialized_pk[0] = execution.lastrowid
                                    if pk_cols and all(value not in (None, "") for value in materialized_pk):
                                        identity_method = "primary_key"
                                        identity_values = materialized_pk
                                    else:
                                        identity_method = "non_primary_key_fallback"
                                        identity_values = [params.get(c) for c in col_names if c not in pk_cols]
                                    provenance["rows"].append({
                                        **trace, "outcome": "inserted", "identity_method": identity_method,
                                        "target_row_key": stable_hash(tuple(str(value) for value in identity_values)),
                                    })
                            else:
                                skipped += 1
                                if provenance is not None:
                                    provenance["rows"].append({**trace, "outcome": "skipped", "reason": "database_ignored"})
                            existing_hashes.add(row_key)
                        except Exception as e:
                            log.warning(f"Skipped row in {table_name}: {e}")
                            failed += 1
                            if provenance is not None:
                                provenance["rows"].append({**trace, "outcome": "failed", "reason": "constraint_or_type_error"})
                    conn.commit()
                    results[table_name] = {"inserted": inserted, "skipped": skipped, "failed": failed, "provenance": provenance}
                    results[table_name]["warnings"] = list(pipeline_warnings)
        for table_name in tables:
            results.setdefault(table_name, {"inserted": 0, "skipped": 0, "failed": 0,
                "warnings": list(pipeline_warnings), "provenance": table_provenance.get(table_name)})
        return results
