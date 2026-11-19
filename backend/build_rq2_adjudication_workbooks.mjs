import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

if (!process.env.ARTIFACT_TOOL_PATH) {
  throw new Error("ARTIFACT_TOOL_PATH must point to artifact_tool.mjs from the bundled runtime");
}
const { SpreadsheetFile, Workbook } = await import(pathToFileURL(process.env.ARTIFACT_TOOL_PATH));

const [inputDir, outputDir, previewDir] = process.argv.slice(2);
if (!inputDir || !outputDir || !previewDir) {
  throw new Error("Usage: node build_rq2_adjudication_workbooks.mjs INPUT_DIR OUTPUT_DIR PREVIEW_DIR");
}

const decisions = [
  "errore",
  "rappresentazione equivalente",
  "alias valido",
  "gold ambiguo",
  "non determinabile",
];
const confidenceLevels = ["bassa", "media", "alta"];
const reviewHeaders = [
  "item_id",
  "dataset",
  "table",
  "natural_key",
  "row_key_columns",
  "column",
  "candidate_value",
  "reference_value",
  "machine_discrepancy_type",
  "alignment_method",
  "decision",
  "confidence",
  "notes",
];

const bodyFont = { name: "Arial", size: 10, color: "#1F2937" };
const headerFormat = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};

function matrix(rows, headers) {
  return [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];
}

async function renderSheet(workbook, sheetName, range, filename) {
  const image = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}

async function buildReviewer(label, inputName, outputName) {
  const items = JSON.parse(await fs.readFile(path.join(inputDir, inputName), "utf8"));
  const workbook = Workbook.create();
  const instructions = workbook.worksheets.add("Instructions");
  const review = workbook.worksheets.add("Review");
  instructions.showGridLines = false;
  review.showGridLines = false;

  instructions.getRange("A2").values = [[`RQ2 blind adjudication - ${label}`]];
  instructions.getRange("A2").format.font = { name: "Arial", size: 14, bold: true, color: "#1F2937" };
  instructions.getRange("A4:B13").values = [
    ["Scopo", "Valutare se le due rappresentazioni conservano lo stesso fatto osservabile."],
    ["Cecità", "Condizione sperimentale, run, modello e punteggi non sono presenti."],
    ["Indipendenza", "Compilare senza consultare l'altro revisore. Il consenso avviene solo dopo il confronto."],
    ["decision: errore", "Le rappresentazioni non sono equivalenti o manca/compare un fatto."],
    ["decision: rappresentazione equivalente", "Il contenuto è semanticamente uguale dopo la canonicalizzazione prevista."],
    ["decision: alias valido", "Il valore usa un alias stabile e non ambiguo dello stesso concetto."],
    ["decision: gold ambiguo", "Il riferimento consente più interpretazioni plausibili."],
    ["decision: non determinabile", "Gli artefatti mostrati non bastano per decidere."],
    ["confidence", "Selezionare bassa, media o alta."],
    ["notes", "Obbligatorie per gold ambiguo e non determinabile; facoltative negli altri casi."],
  ];
  instructions.getRange("A4:A13").format = {
    fill: "#D9EAF7",
    font: { name: "Arial", size: 10, bold: true, color: "#1F2937" },
    verticalAlignment: "top",
  };
  instructions.getRange("B4:B13").format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
  instructions.getRange("A4:B13").format.borders = { preset: "outside", style: "thin", color: "#9CA3AF" };
  instructions.getRange("A:A").format.columnWidth = 34;
  instructions.getRange("B:B").format.columnWidth = 105;
  instructions.getRange("A4:B13").format.autofitRows();

  const values = matrix(items, reviewHeaders);
  review.getRange("A1").write(values);
  review.getRange(`A1:M${values.length}`).format.font = bodyFont;
  review.getRange("A1:M1").format = headerFormat;
  review.getRange(`A2:M${values.length}`).format.verticalAlignment = "top";
  review.getRange(`K2:M${values.length}`).format.fill = "#FFF2CC";
  review.getRange(`K2:K${values.length}`).dataValidation = { rule: { type: "list", values: decisions } };
  review.getRange(`L2:L${values.length}`).dataValidation = { rule: { type: "list", values: confidenceLevels } };
  review.freezePanes.freezeRows(1);
  review.freezePanes.freezeColumns(2);
  review.getRange("A:A").format.columnWidth = 24;
  review.getRange("B:C").format.columnWidth = 16;
  review.getRange("D:E").format.columnWidth = 30;
  review.getRange("F:F").format.columnWidth = 18;
  review.getRange("G:H").format.columnWidth = 55;
  review.getRange("I:J").format.columnWidth = 24;
  review.getRange("K:L").format.columnWidth = 32;
  review.getRange("M:M").format.columnWidth = 50;
  review.getRange(`D2:M${values.length}`).format.wrapText = true;
  review.getRange("1:1").format.rowHeight = 36;

  workbook.recalculate();
  const check = await workbook.inspect({
    kind: "table",
    sheetId: "Review",
    range: "A1:M8",
    include: "values,formulas",
    tableMaxRows: 8,
    tableMaxCols: 13,
    maxChars: 5000,
  });
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 50 },
    summary: `${label} formula error scan`,
    maxChars: 2000,
  });
  console.log(check.ndjson);
  console.log(errors.ndjson);
  await renderSheet(workbook, "Instructions", "A1:B13", `${label.toLowerCase()}_instructions.png`);
  await renderSheet(workbook, "Review", "A1:M18", `${label.toLowerCase()}_review.png`);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(outputDir, outputName));
}

async function buildCoordinator() {
  const rows = JSON.parse(await fs.readFile(path.join(inputDir, "private_mapping.json"), "utf8"));
  const headers = [
    "item_id", "condition", "run", "source_format", "source_ledger", "source_row",
    "source_ledger_sha256", "reviewer_a_order", "reviewer_b_order",
  ];
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("Private mapping");
  sheet.showGridLines = false;
  const values = matrix(rows, headers);
  sheet.getRange("A1").write(values);
  sheet.getRange(`A1:I${values.length}`).format.font = bodyFont;
  sheet.getRange("A1:I1").format = headerFormat;
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("A:A").format.columnWidth = 24;
  sheet.getRange("B:B").format.columnWidth = 16;
  sheet.getRange("C:D").format.columnWidth = 14;
  sheet.getRange("E:E").format.columnWidth = 62;
  sheet.getRange("F:F").format.columnWidth = 12;
  sheet.getRange("G:G").format.columnWidth = 68;
  sheet.getRange("H:I").format.columnWidth = 18;
  sheet.getRange(`E2:G${values.length}`).format.wrapText = true;
  workbook.recalculate();
  const check = await workbook.inspect({
    kind: "table",
    sheetId: "Private mapping",
    range: "A1:I8",
    include: "values,formulas",
    tableMaxRows: 8,
    tableMaxCols: 9,
    maxChars: 5000,
  });
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 50 },
    summary: "coordinator formula error scan",
    maxChars: 2000,
  });
  console.log(check.ndjson);
  console.log(errors.ndjson);
  await renderSheet(workbook, "Private mapping", "A1:I18", "coordinator_mapping.png");
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(outputDir, "coordinator_private_mapping.xlsx"));
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
await buildReviewer("Reviewer A", "reviewer_a_items.json", "reviewer_a.xlsx");
await buildReviewer("Reviewer B", "reviewer_b_items.json", "reviewer_b.xlsx");
await buildCoordinator();
