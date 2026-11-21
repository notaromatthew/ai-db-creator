import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const artifactModule = process.env.ARTIFACT_TOOL_MODULE || "@oai/artifact-tool";
const { SpreadsheetFile, Workbook } = await import(artifactModule);

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const outputDir = path.join(root, "outputs", "gold_standard_consensus");
const previewDir = path.join(outputDir, "_previews");
const data = JSON.parse(await fs.readFile(path.join(outputDir, "consensus_preparation.json"), "utf8"));

const C = {
  navy: "#17365D",
  blue: "#2F5597",
  lightBlue: "#D9EAF7",
  paleYellow: "#FFF2CC",
  paleGreen: "#E2F0D9",
  paleRed: "#FCE4D6",
  gray: "#E7E6E6",
  line: "#B4C6E7",
  white: "#FFFFFF",
  text: "#1F1F1F",
};

function title(sheet, text, subtitle, endCol) {
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[text]];
  sheet.getRange(`A1:${endCol}1`).format = {
    font: { name: "Arial", size: 16, bold: true, color: C.navy },
    rowHeight: 28,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endCol}2`).format = {
    font: { name: "Arial", size: 10, italic: true, color: C.blue },
    rowHeight: 22,
    verticalAlignment: "center",
  };
}

function base(sheet, used) {
  sheet.showGridLines = false;
  sheet.getRange(used).format.font = { name: "Arial", size: 10, color: C.text };
  sheet.getRange(used).format.verticalAlignment = "center";
}

function header(range) {
  range.format = {
    fill: C.navy,
    font: { name: "Arial", size: 10, bold: true, color: C.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    rowHeight: 38,
    borders: { preset: "all", style: "thin", color: C.white },
  };
}

function addSummary(workbook) {
  const s = workbook.worksheets.add("Sintesi");
  s.tabColor = C.navy;
  title(s, "Consenso sui gold standard", "Confronto tecnico indipendente GOLD-A / GOLD-B", "H");
  s.getRange("A4:B10").values = [
    ["Indicatore", "Valore"],
    ["Elementi valutati", data.summary.total_items],
    ["Accordi: entrambi ACCETTA", data.summary.agreement_accept],
    ["Elementi da discutere", data.summary.needs_consensus],
    ["Disaccordi sul verdetto", data.summary.verdict_disagreements],
    ["Decisioni finali registrate", null],
    ["Decisioni ancora aperte", null],
  ];
  header(s.getRange("A4:B4"));
  const decisionRange = `'Da discutere'!O5:O${4 + data.summary.needs_consensus}`;
  s.getRange("B9").formulas = [[`=COUNTIFS(${decisionRange},"ACCETTA")+COUNTIFS(${decisionRange},"MODIFICA")+COUNTIFS(${decisionRange},"ESCLUDI")+COUNTIFS(${decisionRange},"RINVIA")`]];
  s.getRange("B10").formulas = [[`=B7-B9`]];
  s.getRange("A5:A10").format = { fill: C.lightBlue, font: { name: "Arial", size: 10, bold: true, color: C.navy } };
  s.getRange("B5:B10").format = { fill: C.white, horizontalAlignment: "center" };
  s.getRange("A4:B10").format.borders = { preset: "outside", style: "thin", color: C.line };

  s.getRange("D4:H4").values = [["Dataset", "Totale", "Accordi ACCETTA", "Da discutere", "Verdetti diversi"]];
  header(s.getRange("D4:H4"));
  const datasetRows = Object.entries(data.summary.dataset_counts).map(([dataset, values]) => [
    dataset,
    values.total,
    values.agreement_accept,
    values.needs_consensus,
    values.verdict_disagreements,
  ]);
  s.getRange("D5:H7").values = datasetRows;
  s.getRange("D5:D7").format = { fill: C.lightBlue, font: { name: "Arial", size: 10, bold: true, color: C.navy } };
  s.getRange("E5:H7").format.horizontalAlignment = "center";
  s.getRange("D4:H7").format.borders = { preset: "outside", style: "thin", color: C.line };

  s.getRange("A12:B17").values = [
    ["Controllo", "Stato"],
    ["Valutazioni tecniche GOLD-A", "ACQUISITE"],
    ["Valutazioni tecniche GOLD-B", "ACQUISITE"],
    ["Schede personali e firme", "DA INTEGRARE"],
    ["Consenso tecnico", null],
    ["Stato complessivo", null],
  ];
  header(s.getRange("A12:B12"));
  s.getRange("B16").formulas = [[`=IF(B10=0,"COMPLETO","DA COMPLETARE")`]];
  s.getRange("B17").formulas = [[`=IF(AND(B16="COMPLETO",B15="ACQUISITE"),"DOCUMENTAZIONE COMPLETA","IN CORSO")`]];
  s.getRange("A13:A17").format = { fill: C.lightBlue, font: { name: "Arial", size: 10, bold: true, color: C.navy } };
  s.getRange("B13:B17").format.horizontalAlignment = "center";
  s.getRange("A12:B17").format.borders = { preset: "outside", style: "thin", color: C.line };
  s.getRange("B13:B17").conditionalFormats.add("containsText", { text: "DA", format: { fill: C.paleRed, font: { bold: true, color: "#9C0006" } } });
  s.getRange("B13:B17").conditionalFormats.add("containsText", { text: "ACQUISITE", format: { fill: C.paleGreen, font: { bold: true, color: "#375623" } } });
  s.getRange("B13:B17").conditionalFormats.add("containsText", { text: "COMPLETO", format: { fill: C.paleGreen, font: { bold: true, color: "#375623" } } });

  s.getRange("D12:H17").merge();
  s.getRange("D12").values = [[
    "Le schede personali non sono necessarie per confrontare i giudizi tecnici. Prima della chiusura formale della validazione devono però essere aggiunte le qualifiche, la dichiarazione d'indipendenza, la data e la firma di entrambi. Nessuna correzione al gold standard è considerata approvata finché i campi di consenso non sono completati e confermati da GOLD-A e GOLD-B."
  ]];
  s.getRange("D12:H17").format = { fill: C.gray, font: { name: "Arial", size: 10, italic: true, color: C.text }, wrapText: true, verticalAlignment: "center" };
  s.getRange("A4:A17").format.columnWidth = 38;
  s.getRange("B4:B17").format.columnWidth = 24;
  s.getRange("C1:C18").format.columnWidth = 3;
  s.getRange("D4:D17").format.columnWidth = 20;
  s.getRange("E4:H17").format.columnWidth = 18;
  s.getRange("A4:H17").format.autofitRows();
  base(s, "A1:H18");
}

function discussionRow(item) {
  return [
    item.dataset,
    item.item_id,
    item.area,
    item.object,
    item.criterion,
    item.comparison_status,
    item.a.verdict,
    item.a.severity,
    item.a.correction,
    item.a.rationale,
    item.b.verdict,
    item.b.severity,
    item.b.correction,
    item.b.rationale,
    "", "", "", "", "", "", "",
  ];
}

function addDiscussion(workbook) {
  const items = data.items.filter((x) => x.needs_consensus);
  const s = workbook.worksheets.add("Da discutere");
  s.tabColor = "#C65911";
  title(s, "Elementi da discutere", "Compilare i campi gialli durante il confronto congiunto.", "U");
  const headers = [[
    "Dataset", "Item ID", "Area", "Oggetto", "Criterio", "Tipo di differenza",
    "Verdetto A", "Gravità A", "Correzione A", "Motivazione A",
    "Verdetto B", "Gravità B", "Correzione B", "Motivazione B",
    "Decisione finale", "Gravità finale", "Correzione concordata", "Motivazione del consenso",
    "Conferma GOLD-A", "Conferma GOLD-B", "Data consenso",
  ]];
  const rows = items.map(discussionRow);
  const end = 4 + rows.length;
  s.getRange(`A4:U${end}`).values = [...headers, ...rows];
  header(s.getRange("A4:U4"));
  s.getRange(`A5:N${end}`).format.fill = C.white;
  s.getRange(`O5:U${end}`).format.fill = C.paleYellow;
  s.getRange(`A5:U${end}`).format.wrapText = true;
  s.getRange(`A5:U${end}`).format.verticalAlignment = "top";
  s.getRange(`A5:U${end}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  s.getRange(`O5:O${end}`).dataValidation = { rule: { type: "list", values: ["ACCETTA", "MODIFICA", "ESCLUDI", "RINVIA"] } };
  s.getRange(`P5:P${end}`).dataValidation = { rule: { type: "list", values: ["N/A", "CRITICA", "MAGGIORE", "MINORE"] } };
  s.getRange(`S5:T${end}`).dataValidation = { rule: { type: "list", values: ["CONFERMO", "NON CONFERMO"] } };
  s.getRange(`U5:U${end}`).setNumberFormat("dd/mm/yyyy");
  s.getRange(`F5:F${end}`).conditionalFormats.add("containsText", { text: "DISACCORDO", format: { fill: C.paleRed, font: { bold: true, color: "#9C0006" } } });
  s.getRange(`F5:F${end}`).conditionalFormats.add("containsText", { text: "ACCORDO_MODIFICA", format: { fill: C.paleYellow, font: { bold: true, color: "#7F6000" } } });
  s.getRange(`O5:O${end}`).conditionalFormats.add("containsText", { text: "MODIFICA", format: { fill: C.paleRed, font: { bold: true, color: "#9C0006" } } });
  s.getRange(`O5:O${end}`).conditionalFormats.add("containsText", { text: "ACCETTA", format: { fill: C.paleGreen, font: { bold: true, color: "#375623" } } });
  const widths = [12, 11, 12, 26, 45, 32, 13, 13, 48, 56, 13, 13, 48, 56, 17, 15, 52, 56, 18, 18, 16];
  widths.forEach((w, i) => s.getRangeByIndexes(0, i, end, 1).format.columnWidth = w);
  s.getRange(`A5:U${end}`).format.autofitRows();
  s.freezePanes.freezeRows(4);
  s.freezePanes.freezeColumns(2);
  base(s, `A1:U${end}`);
}

function addAgreements(workbook) {
  const items = data.items.filter((x) => !x.needs_consensus);
  const s = workbook.worksheets.add("Accordi");
  s.tabColor = "#70AD47";
  title(s, "Accordi senza discussione", "Entrambi i valutatori hanno espresso ACCETTA.", "K");
  const rows = items.map((item) => [
    item.dataset, item.item_id, item.area, item.object, item.criterion,
    item.a.rationale, item.a.notes, item.b.rationale, item.b.notes,
    item.a.verdict, item.comparison_status,
  ]);
  const end = 4 + rows.length;
  s.getRange(`A4:K${end}`).values = [["Dataset", "Item ID", "Area", "Oggetto", "Criterio", "Motivazione A", "Note A", "Motivazione B", "Note B", "Verdetto comune", "Stato"], ...rows];
  header(s.getRange("A4:K4"));
  s.getRange(`A5:K${end}`).format.wrapText = true;
  s.getRange(`A5:K${end}`).format.verticalAlignment = "top";
  s.getRange(`J5:K${end}`).format.fill = C.paleGreen;
  s.getRange(`A5:K${end}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  const widths = [12, 11, 12, 24, 44, 54, 34, 54, 34, 16, 24];
  widths.forEach((w, i) => s.getRangeByIndexes(0, i, end, 1).format.columnWidth = w);
  s.getRange(`A5:K${end}`).format.autofitRows();
  s.freezePanes.freezeRows(4);
  s.freezePanes.freezeColumns(2);
  base(s, `A1:K${end}`);
}

function addAll(workbook) {
  const s = workbook.worksheets.add("Tutte le valutazioni");
  title(s, "Audit completo delle valutazioni", "Valori normalizzati per il confronto; i file originali restano invariati.", "P");
  const rows = data.items.map((item) => [
    item.dataset, item.item_id, item.area, item.artifact, item.object, item.criterion,
    item.a.verdict, item.a.severity, item.a.correction, item.a.rationale,
    item.b.verdict, item.b.severity, item.b.correction, item.b.rationale,
    item.comparison_status, item.needs_consensus ? "SI" : "NO",
  ]);
  const end = 4 + rows.length;
  s.getRange(`A4:P${end}`).values = [[
    "Dataset", "Item ID", "Area", "Artefatto", "Oggetto", "Criterio",
    "Verdetto A", "Gravità A", "Correzione A", "Motivazione A",
    "Verdetto B", "Gravità B", "Correzione B", "Motivazione B",
    "Stato confronto", "Consenso richiesto",
  ], ...rows];
  header(s.getRange("A4:P4"));
  s.getRange(`A5:P${end}`).format.wrapText = true;
  s.getRange(`A5:P${end}`).format.verticalAlignment = "top";
  s.getRange(`A5:P${end}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  s.getRange(`P5:P${end}`).conditionalFormats.add("containsText", { text: "SI", format: { fill: C.paleRed, font: { bold: true, color: "#9C0006" } } });
  s.getRange(`P5:P${end}`).conditionalFormats.add("containsText", { text: "NO", format: { fill: C.paleGreen, font: { bold: true, color: "#375623" } } });
  const widths = [12, 11, 12, 24, 24, 42, 13, 13, 46, 52, 13, 13, 46, 52, 33, 19];
  widths.forEach((w, i) => s.getRangeByIndexes(0, i, end, 1).format.columnWidth = w);
  s.getRange(`A5:P${end}`).format.autofitRows();
  s.freezePanes.freezeRows(4);
  s.freezePanes.freezeColumns(2);
  base(s, `A1:P${end}`);
}

function addInstructions(workbook) {
  const s = workbook.worksheets.add("Istruzioni");
  s.tabColor = C.blue;
  title(s, "Procedura di consenso", "Da svolgere solo dopo le due valutazioni indipendenti.", "H");
  const rows = [
    ["1. Preparazione", "Il coordinatore apre Da discutere. I file originali GOLD-A e GOLD-B non devono essere modificati."],
    ["2. Ordine", "Esaminare prima i disaccordi sul verdetto, poi gli accordi su MODIFICA con gravità o formulazioni diverse."],
    ["3. Evidenza", "Confrontare le motivazioni con schema, ground truth, fonti ed evaluation_spec. Non decidere per semplice maggioranza."],
    ["4. Decisione finale", "Scegliere ACCETTA, MODIFICA, ESCLUDI o RINVIA. MODIFICA richiede gravità, testo della correzione e motivazione."],
    ["5. Conferme", "GOLD-A e GOLD-B selezionano CONFERMO sulla stessa riga dopo avere concordato la formulazione finale."],
    ["6. Data", "Inserire la data reale della decisione. Non retrodatare il consenso."],
    ["7. Controllo", "Il foglio Sintesi deve mostrare zero decisioni aperte. Le schede personali possono essere aggiunte successivamente, ma prima della chiusura formale."],
    ["8. Applicazione", "Solo dopo il consenso si correggono gold_schema.json, ground_truth.db, evaluation_spec.json, fonti o documentazione. Ogni modifica deve essere versionata e rigenerata in modo riproducibile."],
    ["9. Tracciabilità", "Conservare i due XLSX originali, questo file compilato, il manifest degli input e gli hash degli artefatti corretti."],
  ];
  s.getRange("A4:B12").values = rows;
  s.getRange("A4:A12").format = { fill: C.lightBlue, font: { name: "Arial", size: 10, bold: true, color: C.navy }, wrapText: true, verticalAlignment: "top" };
  s.getRange("B4:B12").format = { fill: C.white, wrapText: true, verticalAlignment: "top" };
  s.getRange("A4:B12").format.borders = { preset: "outside", style: "thin", color: C.line };
  s.getRange("A4:A12").format.columnWidth = 25;
  s.getRange("B4:B12").format.columnWidth = 105;
  s.getRange("A4:B12").format.autofitRows();
  base(s, "A1:H14");
}

const workbook = Workbook.create();
addSummary(workbook);
addDiscussion(workbook);
addAgreements(workbook);
addAll(workbook);
addInstructions(workbook);
workbook.recalculate();

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "Sintesi!A4:H17",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 10,
  maxChars: 10000,
});
console.log(summaryCheck.ndjson);
const errorCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "consensus workbook formula error scan",
});
console.log(errorCheck.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range] of [
  ["Sintesi", "A1:H18"],
  ["Da discutere", "A1:U15"],
  ["Accordi", "A1:K15"],
  ["Tutte le valutazioni", "A1:P15"],
  ["Istruzioni", "A1:H14"],
]) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(outputDir, "Consenso_gold_standard_GOLD-A_GOLD-B.xlsx");
await output.save(outputPath);
console.log(outputPath);
