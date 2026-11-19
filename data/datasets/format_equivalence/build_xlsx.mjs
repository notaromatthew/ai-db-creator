import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

if (!process.env.ARTIFACT_TOOL_PATH) throw new Error("ARTIFACT_TOOL_PATH is required");
const { SpreadsheetFile, Workbook } = await import(pathToFileURL(process.env.ARTIFACT_TOOL_PATH));
const [csvPath, outputPath, previewPath] = process.argv.slice(2);
const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Enrollments" });
const sheet = workbook.worksheets.getItem("Enrollments");
sheet.showGridLines = false;
const used = sheet.getUsedRange();
used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
sheet.getRange("A1:G1").format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
sheet.freezePanes.freezeRows(1);
sheet.getRange("A:A").format.columnWidth = 24;
sheet.getRange("B:B").format.columnWidth = 34;
sheet.getRange("C:C").format.columnWidth = 16;
sheet.getRange("D:D").format.columnWidth = 34;
sheet.getRange("E:G").format.columnWidth = 14;
workbook.recalculate();
const check = await workbook.inspect({
  kind: "table", sheetId: "Enrollments", range: "A1:G10", include: "values,formulas",
  tableMaxRows: 10, tableMaxCols: 7, maxChars: 5000,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 50 },
  summary: "format fixture formula error scan",
  maxChars: 2000,
});
console.log(check.ndjson);
console.log(errors.ndjson);
const preview = await workbook.render({ sheetName: "Enrollments", range: "A1:G18", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
