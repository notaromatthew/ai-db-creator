from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.config import settings
from app.models.schema_models import NormalizedSchema, QueryResponse
from app.utils.exceptions import LLMException
from app.utils.logger import log
import re
from app.utils.research import sha256_text


def _get_llm(temperature: float = 0.1, force_local: bool = False):
    provider = "ollama" if (force_local or settings.use_ollama) else settings.llm_provider

    if provider == "ollama":
        model = _detect_local_model()
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
        )

    if provider == "groq":
        return ChatOpenAI(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "openrouter":
        return ChatOpenAI(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            temperature=temperature,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/ai-db-creator",
                "X-Title": "AI DB Creator",
            },
        )

    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                api_key=settings.google_api_key,
                model=settings.google_model,
                temperature=temperature,
            )
        except ImportError:
            log.warning("langchain-google-genai not installed. Falling back to OpenAI.")
            return ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_model, temperature=temperature)

    return ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_model, temperature=temperature)


schema_parser = PydanticOutputParser(pydantic_object=NormalizedSchema)

SCHEMA_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a database normalization expert. Generate a 3NF normalized database schema.
Rules:
- All tables must be in 3NF (no transitive dependencies)
- Use snake_case for names, plural for tables
- Every table must have a primary key
- Foreign keys must reference existing tables
- Choose appropriate SQL data types (INTEGER, TEXT, REAL, DATE, BOOLEAN)"""),
    ("user", "User description: {prompt}\n\nDocument context:\n{document_context}\n\n{format_instructions}"),
])

QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a SQL expert. Generate valid {dialect} SQL queries from natural language descriptions.\n"
               "CRITICAL: Output ONLY the raw SQL query. Do NOT use markdown code blocks, backticks, or any formatting. "
               "Do NOT wrap the SQL in ```sql ... ```. Just output the SQL statement directly."),
    ("user", "Database schema:\n{schema}\n\nUser request: {prompt}\nGenerate only the SQL query, no explanation."),
])


async def generate_schema(prompt: str, document_context: str = "") -> NormalizedSchema:
    try:
        llm = _get_llm()
        chain = SCHEMA_PROMPT | llm | schema_parser
        result = await chain.ainvoke({
            "prompt": prompt,
            "document_context": document_context,
            "format_instructions": schema_parser.get_format_instructions(),
        })
        log.info(f"Generated schema with {len(result.tables)} tables")
        return result
    except Exception as e:
        log.error(f"Schema generation failed ({type(e).__name__})")
        raise LLMException(detail="Schema generation failed") from e


async def generate_data_for_table(table_def, text_content: str) -> list[dict]:
    """Generate structured data rows from document text using LLM."""
    from langchain_core.output_parsers import JsonOutputParser

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a data extraction assistant. Extract structured data from the provided document text "
                   "matching the given table schema. The text may contain tabular data (CSV/Excel) exported as text, "
                   "or free-form document text.\n"
                   "Rules:\n- Extract values that match the column data types\n- Use null for missing values\n"
                   "- Return an empty array if no matching data is found\n"
                   "- Do NOT include explanations or markdown\n"
                   "- Return ONLY a JSON array of objects."),
        ("user", "Table name: {table_name}\nColumns:\n{columns}\n\nDocument text:\n{document_text}\n\nReturn JSON array of objects."),
    ])

    try:
        llm = _get_llm(temperature=0.0)
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({
            "table_name": table_def.name,
            "columns": "\n".join(f"- {c.name} ({c.data_type}){' PK' if c.is_primary_key else ''}{' FK → '+c.foreign_key_table+'.'+c.foreign_key_column if c.is_foreign_key else ''}" for c in table_def.columns),
            "document_text": text_content[:20000],
        })
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except Exception as e:
        log.warning(f"LLM data generation failed for {table_def.name} ({type(e).__name__})")
        return []


async def map_columns_to_tables(headers: list[str], sample_rows: list[list], schema_tables: list, relationships: list | None = None) -> dict[str, dict[int, str]]:
    """Use LLM to map document columns to correct schema tables/columns.
    Returns {table_name: {column_index: schema_column_name}}."""
    from langchain_core.output_parsers import JsonOutputParser

    tables_desc = []
    for t in schema_tables:
        pk_cols = [c.name for c in t.columns if c.is_primary_key]
        fk_cols = [f"{c.name}→{c.foreign_key_table}.{c.foreign_key_column}" for c in t.columns if c.is_foreign_key]
        parts = []
        for c in t.columns:
            label = c.name
            if c.is_primary_key:
                label += " 🔑PK"
            if c.is_foreign_key:
                label += f" 🔗FK→{c.foreign_key_table}.{c.foreign_key_column}"
            parts.append(f"{c.name} ({c.data_type})")
        tables_desc.append(f"- {t.name}: {', '.join(parts)}")

    rels_desc = []
    if relationships:
        for r in relationships:
            rels_desc.append(f"{r.from_table}.{r.from_column} → {r.to_table}.{r.to_column}")

    sample = "\n".join(" | ".join(str(v) for v in row) for row in sample_rows[:3])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You map columns from a denormalized file (CSV/XLS) to the correct normalized database tables. "
                   "Rules:\n"
                   "- Return JSON: {{\"table_name\": {{\"column_index\": \"schema_column_name\"}}}}\n"
                   "- Column indices are 0-based integers (NOT strings)\n"
                   "- A file column can map to columns in MULTIPLE tables (e.g. a customer code → PK in clienti AND FK in scontrini)\n"
                   "- Map EVERY column that has matching data in the schema\n"
                   "- Use the RELATIONSHIPS to find FK references: if a column maps to a PK, check if any other table has an FK reference to it\n"
                   "- Do NOT include tables/columns that have no matching data in the document\n"
                   "Example: {{\"clienti\": {{0: \"codice_fiscale\", 1: \"nome\"}}, \"scontrini\": {{0: \"codice_fiscale_cliente\", 3: \"id_scontrino\"}}}}\n"
                   "The response must be a valid JSON object with table names as keys."),
        ("user", "Database tables:\n{tables}\nRelationships:\n{relationships}\n\nDocument headers: {headers}\nSample rows:\n{sample}\n\nReturn JSON mapping."),
    ])

    try:
        llm = _get_llm(temperature=0.0)
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({
            "tables": "\n".join(tables_desc),
            "relationships": "\n".join(rels_desc) if rels_desc else "none",
            "headers": " | ".join(f"[{i}] {h}" for i, h in enumerate(headers)),
            "sample": sample,
        })
        mapping = {}
        for tn, cols in result.items():
            if isinstance(cols, dict):
                mapping[tn] = {int(k): v for k, v in cols.items()}
        return mapping
    except Exception as e:
        log.warning(f"LLM column mapping failed ({type(e).__name__})")
        return {}


async def generate_query(prompt: str, schema: str, dialect: str = "sqlite") -> QueryResponse:
    try:
        llm = _get_llm(temperature=0.0)
        chain = QUERY_PROMPT | llm
        result = await chain.ainvoke({
            "prompt": prompt,
            "schema": schema,
            "dialect": dialect,
        })
        return QueryResponse(sql=result.content.strip())
    except Exception as e:
        log.error(f"Query generation failed ({type(e).__name__})")
        raise LLMException(detail="Query generation failed") from e

def _detect_local_model():
    """Auto-detect available local LLM."""
    try:
        import ollama
        client = ollama.Client(host=settings.ollama_base_url)
        models = client.list()
        if models and 'models' in models:
            return models['models'][0]['name']
    except:
        pass
    return settings.ollama_model

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "google": "Google Gemini",
    "ollama": "Ollama (locale)",
}

def get_llm_info():
    """Get current LLM configuration info."""
    provider = "ollama" if settings.use_ollama else settings.llm_provider
    label = _PROVIDER_LABELS.get(provider, provider.capitalize())

    models = {
        "openai": settings.openai_model,
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
        "google": settings.google_model,
        "ollama": _detect_local_model(),
    }
    model = models.get(provider, settings.openai_model)

    return {
        'provider': label,
        'model': model,
    }


def get_llm_run_metadata(temperature: float, prompt_text: str, document_hashes: list[str] | None = None, input_label: str = "prompt") -> dict:
    """Public, secret-free model metadata suitable for research logs."""
    info = get_llm_info()
    return {
        "provider": info["provider"],
        "model": info["model"],
        "parameters": {"temperature": temperature},
        f"{input_label}_hash": sha256_text(prompt_text),
        "document_hashes": document_hashes or [],
    }


POPULATE_SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a SQL database population expert. Your task is to generate valid SQLite `INSERT OR IGNORE INTO` SQL statements to populate a normalized database using real data extracted from provided documents.

Rules:
1. Output ONLY valid SQLite INSERT statements (use `INSERT OR IGNORE INTO table_name (col1, col2, ...) VALUES (val1, val2, ...);`).
2. Insert ALL data extracted from the documents into ALL relevant tables in the schema.
3. Strictly maintain primary key and foreign key values across related tables (e.g., if a receipt belongs to a customer, use the exact same fiscal code in both the customers table and the receipts table).
4. Correctly map document columns/fields to the corresponding schema table columns.
5. Format dates as ISO strings (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS), escape single quotes in strings (e.g., O''Connor -> O''Connor).
6. For columns marked NOT NULL in the schema, NEVER use NULL; use '' for text, 0 for numbers, or a reasonable default.
7. CRITICAL: Output ONLY raw SQL statements separated by semicolons. Do NOT use markdown code blocks, backticks (```sql ... ```), or explanation text."""),
    ("user", "Database Schema:\n{schema_info}\n\nDocument Data:\n{doc_content}\n\nGenerate all INSERT SQL statements:"),
])


async def generate_sql_for_population(schema: NormalizedSchema, document_content: str) -> str:
    """Use LLM to generate SQL INSERT statements for populating the database from documents."""
    schema_parts = []
    for t in schema.tables:
        cols = []
        for c in t.columns:
            col_str = f"{c.name} {c.data_type}"
            if c.is_primary_key:
                col_str += " PRIMARY KEY"
            if c.is_not_null:
                col_str += " NOT NULL"
            if c.is_foreign_key:
                col_str += f" REFERENCES {c.foreign_key_table}({c.foreign_key_column})"
            cols.append(col_str)
        schema_parts.append(f"CREATE TABLE {t.name} (\n  " + ",\n  ".join(cols) + "\n);")

    if schema.relationships:
        schema_parts.append("Relationships:")
        for r in schema.relationships:
            schema_parts.append(f"- {r.from_table}.{r.from_column} -> {r.to_table}.{r.to_column} ({r.type})")

    schema_info = "\n\n".join(schema_parts)

    try:
        llm = _get_llm(temperature=0.1)
        chain = POPULATE_SQL_PROMPT | llm
        result = await chain.ainvoke({
            "schema_info": schema_info,
            "doc_content": document_content[:40000],
        })
        sql_text = result.content.strip()
        sql_text = re.sub(r'```\w*', '', sql_text)
        sql_text = sql_text.replace('```', '').strip()
        return sql_text
    except Exception as e:
        log.error(f"Failed to generate population SQL ({type(e).__name__})")
        return ""
