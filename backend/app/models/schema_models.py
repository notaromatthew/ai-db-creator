from pydantic import BaseModel, Field
from typing import Literal


class ColumnDef(BaseModel):
    name: str = Field(description="Column name in snake_case")
    data_type: str = Field(description="SQL data type (INTEGER, TEXT, REAL, DATE, BOOLEAN, etc.)")
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: str | None = None
    foreign_key_column: str | None = None
    is_unique: bool = False
    is_not_null: bool = False
    default_value: str | None = None
    description: str | None = Field(default=None, description="What this column stores")


class TableDef(BaseModel):
    name: str = Field(description="Table name in snake_case, plural")
    columns: list[ColumnDef]
    description: str | None = Field(default=None, description="What this table represents")


class RelationshipDef(BaseModel):
    type: Literal["one_to_many", "many_to_many", "one_to_one"]
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class NormalizedSchema(BaseModel):
    tables: list[TableDef]
    relationships: list[RelationshipDef]
    description: str | None = Field(default=None, description="Overview of what this database models")


class SchemaUpdate(BaseModel):
    tables: list[TableDef]


class QueryRequest(BaseModel):
    prompt: str
    dialect: str = "sqlite"


class QueryResponse(BaseModel):
    sql: str
    explanation: str | None = None


class GenerateRequest(BaseModel):
    prompt: str
    document_ids: list[str] = []
    condition: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    participant_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")


class PopulateRequest(BaseModel):
    document_ids: list[str] = []
    condition: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    participant_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")

class ExecuteQueryRequest(BaseModel):
    sql: str

class ExecuteQueryResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    affected: int | None = None
