# RQ2 format-equivalence fixture

This dataset supports a causal comparison of file formats. `records.csv`,
`records.xlsx`, `records.txt`, and `records.pdf` encode the same 45 enrollment
facts and the same seven fields. Only one file is loaded in each format cell.

The gold schema, SQLite database and evaluation specification are copied from
the frozen University dataset. `fixture_manifest.json` records hashes after all
representations have been generated and validated.

Generation order:

1. `python prepare_fixture.py`
2. build `source/records.xlsx` with `build_xlsx.mjs` and the bundled artifact runtime
3. build `source/records.pdf` with `build_pdf.py` and ReportLab
4. `python prepare_fixture.py` is not rerun; call `finalize_manifest()`
5. `python validate_fixture.py`

Format-comparison runs must use a new output directory, a single software
revision and a preregistered interleaved schedule. They must not be combined
with the earlier heterogeneous `combined` matrix.
