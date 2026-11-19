import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

if (!process.env.ARTIFACT_TOOL_PATH) {
  throw new Error("ARTIFACT_TOOL_PATH must point to artifact_tool.mjs from the bundled runtime");
}
const { SpreadsheetFile, Workbook } = await import(pathToFileURL(process.env.ARTIFACT_TOOL_PATH));

const [csvPath, summaryPath, outputPath, previewDir] = process.argv.slice(2);
if (!csvPath || !summaryPath || !outputPath || !previewDir) {
  throw new Error("Usage: node build_rq2_consensus_workbook.mjs CSV SUMMARY OUTPUT PREVIEW_DIR");
}

const decisions = [
  "errore",
  "rappresentazione equivalente",
  "alias valido",
  "gold ambiguo",
  "non determinabile",
];
const summary = JSON.parse(await fs.readFile(summaryPath, "utf8"));
const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Consenso" });
const consensus = workbook.worksheets.getItem("Consenso");
const instructions = workbook.worksheets.add("Istruzioni");
const lastRow = summary.disagreement_count + 1;
const bodyFont = { name: "Arial", size: 10, color: "#1F2937" };
const headerFormat = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};

consensus.showGridLines = false;
consensus.getRange(`A1:N${lastRow}`).format.font = bodyFont;
consensus.getRange("A1:N1").format = headerFormat;
consensus.getRange(`A2:N${lastRow}`).format.verticalAlignment = "top";
consensus.getRange(`D2:N${lastRow}`).format.wrapText = true;
consensus.getRange(`M2:N${lastRow}`).format.fill = "#FFF2CC";
consensus.getRange(`M2:M${lastRow}`).dataValidation = {
  rule: { type: "list", values: decisions },
};
consensus.getRange(`M2:M${lastRow}`).conditionalFormats.add("containsBlanks", {
  format: { fill: "#FCE8E6", font: { color: "#B91C1C", bold: true } },
});
consensus.getRange(`N2:N${lastRow}`).conditionalFormats.add("containsBlanks", {
  format: { fill: "#FCE8E6" },
});
consensus.freezePanes.freezeRows(1);
consensus.freezePanes.freezeColumns(3);
consensus.getRange("A:A").format.columnWidth = 24;
consensus.getRange("B:C").format.columnWidth = 16;
consensus.getRange("D:D").format.columnWidth = 34;
consensus.getRange("E:F").format.columnWidth = 55;
consensus.getRange("G:G").format.columnWidth = 30;
consensus.getRange("H:H").format.columnWidth = 15;
consensus.getRange("I:I").format.columnWidth = 60;
consensus.getRange("J:J").format.columnWidth = 30;
consensus.getRange("K:K").format.columnWidth = 15;
consensus.getRange("L:L").format.columnWidth = 60;
consensus.getRange("M:M").format.columnWidth = 34;
consensus.getRange("N:N").format.columnWidth = 60;
consensus.getRange("1:1").format.rowHeight = 38;
const table = consensus.tables.add(`A1:N${lastRow}`, true, "ConsensusTable");
table.style = "TableStyleMedium2";
table.showBandedRows = true;
table.showFilterButton = true;

instructions.showGridLines = false;
instructions.getRange("A2").values = [["RQ2 - consenso sui disaccordi"]];
instructions.getRange("A2").format.font = { name: "Arial", size: 14, bold: true, color: "#1F2937" };
instructions.getRange("A4:B9").values = [
  ["Elementi valutati", summary.item_count],
  ["Accordi esatti", summary.exact_agreement_count],
  ["Accordo esatto", summary.exact_agreement_rate],
  ["Accordo atteso per caso", summary.expected_agreement_rate],
  ["Kappa di Cohen nominale", summary.cohen_kappa_nominal],
  ["Disaccordi da risolvere", summary.disagreement_count],
];
instructions.getRange("A4:A9").format = {
  fill: "#D9EAF7",
  font: { name: "Arial", size: 10, bold: true, color: "#1F2937" },
};
instructions.getRange("B4:B9").format.font = bodyFont;
instructions.getRange("B6:B7").format.numberFormat = "0.0%";
instructions.getRange("B8:B8").format.numberFormat = "0.000";
instructions.getRange("A11:B18").values = [
  ["Procedura", "I due revisori discutono soltanto le righe di Consenso. La condizione sperimentale resta nascosta fino al blocco definitivo delle decisioni."],
  ["Campi da compilare", "Per ogni riga selezionare consensus_decision e scrivere una motivazione sintetica in consensus_notes."],
  ["Regola", "La decisione finale deve derivare dal confronto degli artefatti mostrati, non dalla maggioranza o dalla confidenza dichiarata."],
  ["errore", "Le rappresentazioni non sono equivalenti o manca/compare un fatto."],
  ["rappresentazione equivalente", "Il contenuto conserva lo stesso fatto osservabile dopo la canonicalizzazione prevista."],
  ["alias valido", "Il valore usa un alias stabile e non ambiguo dello stesso concetto."],
  ["gold ambiguo", "Il riferimento consente più interpretazioni plausibili."],
  ["non determinabile", "Gli artefatti mostrati non bastano per decidere."],
];
instructions.getRange("A11:A18").format = {
  fill: "#D9EAF7",
  font: { name: "Arial", size: 10, bold: true, color: "#1F2937" },
  verticalAlignment: "top",
};
instructions.getRange("B11:B18").format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
instructions.getRange("A4:B9").format.borders = { preset: "outside", style: "thin", color: "#9CA3AF" };
instructions.getRange("A11:B18").format.borders = { preset: "outside", style: "thin", color: "#9CA3AF" };
instructions.getRange("A:A").format.columnWidth = 34;
instructions.getRange("B:B").format.columnWidth = 105;
instructions.getRange("A4:B18").format.autofitRows();

workbook.recalculate();
const check = await workbook.inspect({
  kind: "table",
  sheetId: "Consenso",
  range: "A1:N8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 14,
  maxChars: 6000,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 50 },
  summary: "consensus formula error scan",
  maxChars: 2000,
});
console.log(check.ndjson);
console.log(errors.ndjson);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range, filename] of [
  ["Consenso", "A1:N16", "consensus.png"],
  ["Istruzioni", "A1:B18", "instructions.png"],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
