from app.models.schema_models import ColumnDef, NormalizedSchema, RelationshipDef, TableDef


def valid_schema(extra_column: str | None = None) -> NormalizedSchema:
    libri_columns = [
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ColumnDef(name="titolo", data_type="TEXT"),
        ColumnDef(name="autore_id", data_type="INTEGER", is_foreign_key=True,
                  foreign_key_table="autori", foreign_key_column="id"),
    ]
    if extra_column:
        libri_columns.append(ColumnDef(name=extra_column, data_type="TEXT"))
    return NormalizedSchema(
        tables=[
            TableDef(name="autori", columns=[
                ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnDef(name="nome", data_type="TEXT"),
            ]),
            TableDef(name="libri", columns=libri_columns),
        ],
        relationships=[RelationshipDef(type="one_to_many", from_table="autori", from_column="id",
                                       to_table="libri", to_column="autore_id")],
    )


def invalid_schema() -> NormalizedSchema:
    """Senza chiave primaria in 'libri', con FK verso una tabella inesistente e un tipo non ammesso."""
    return NormalizedSchema(
        tables=[
            TableDef(name="autori", columns=[
                ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnDef(name="nome", data_type="BLOBBY"),
            ]),
            TableDef(name="libri", columns=[
                ColumnDef(name="titolo", data_type="TEXT"),
                ColumnDef(name="editore_id", data_type="INTEGER", is_foreign_key=True,
                          foreign_key_table="editori", foreign_key_column="id"),
            ]),
        ],
        relationships=[],
    )
