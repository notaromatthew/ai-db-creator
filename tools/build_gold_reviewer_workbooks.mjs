import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const artifactModule = process.env.ARTIFACT_TOOL_MODULE || "@oai/artifact-tool";
const { SpreadsheetFile, Workbook } = await import(artifactModule);

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const outputDir = path.join(root, "outputs", "gold_standard_validation");
const previewDir = path.join(outputDir, "_xlsx_previews");
const datasetsDir = path.join(root, "data", "datasets");

const COLORS = {
  navy: "#17365D",
  blue: "#2F5597",
  lightBlue: "#D9EAF7",
  paleYellow: "#FFF2CC",
  paleGreen: "#E2F0D9",
  paleRed: "#FCE4D6",
  paleGray: "#E7E6E6",
  line: "#B4C6E7",
  text: "#1F1F1F",
  white: "#FFFFFF",
};

const DATASETS = [
  { key: "university", label: "University", prefix: "U" },
  { key: "library", label: "Library", prefix: "L" },
  { key: "hospital", label: "Hospital", prefix: "H" },
];

const verdicts = ["ACCETTA", "MODIFICA", "INCERTO"];
const severities = ["N/A", "CRITICA", "MAGGIORE", "MINORE"];

function title(sheet, text, subtitle, endCol = "J") {
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[text]];
  sheet.getRange(`A1:${endCol}1`).format = {
    font: { name: "Arial", size: 16, bold: true, color: COLORS.navy },
    verticalAlignment: "center",
    rowHeight: 28,
  };
  sheet.getRange(`A2:${endCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endCol}2`).format = {
    font: { name: "Arial", size: 10, italic: true, color: COLORS.blue },
    verticalAlignment: "center",
    rowHeight: 22,
  };
}

function styleBase(sheet, usedRange) {
  sheet.showGridLines = false;
  sheet.getRange(usedRange).format.font = { name: "Arial", size: 10, color: COLORS.text };
  sheet.getRange(usedRange).format.verticalAlignment = "center";
}

function styleHeader(range) {
  range.format = {
    fill: COLORS.navy,
    font: { name: "Arial", size: 10, bold: true, color: COLORS.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    rowHeight: 36,
    borders: { preset: "all", style: "thin", color: COLORS.white },
  };
}

function styleInput(range) {
  range.format.fill = COLORS.paleYellow;
  range.format.borders = { preset: "outside", style: "thin", color: COLORS.line };
}

function addReviewFormatting(sheet, startRow, endRow, verdictCol, severityCol, inputStartCol, inputEndCol) {
  sheet.getRange(`${inputStartCol}${startRow}:${inputEndCol}${endRow}`).format.fill = COLORS.paleYellow;
  sheet.getRange(`${inputStartCol}${startRow}:${inputEndCol}${endRow}`).format.wrapText = true;
  sheet.getRange(`${verdictCol}${startRow}:${verdictCol}${endRow}`).dataValidation = {
    rule: { type: "list", values: verdicts },
  };
  sheet.getRange(`${severityCol}${startRow}:${severityCol}${endRow}`).dataValidation = {
    rule: { type: "list", values: severities },
  };
  sheet.getRange(`${verdictCol}${startRow}:${verdictCol}${endRow}`).conditionalFormats.add("containsText", {
    text: "MODIFICA",
    format: { fill: COLORS.paleRed, font: { bold: true, color: "#9C0006" } },
  });
  sheet.getRange(`${verdictCol}${startRow}:${verdictCol}${endRow}`).conditionalFormats.add("containsText", {
    text: "ACCETTA",
    format: { fill: COLORS.paleGreen, font: { bold: true, color: "#375623" } },
  });
  sheet.getRange(`${verdictCol}${startRow}:${verdictCol}${endRow}`).conditionalFormats.add("containsText", {
    text: "INCERTO",
    format: { fill: COLORS.paleYellow, font: { bold: true, color: "#7F6000" } },
  });
}

function addInstructions(workbook, code) {
  const sheet = workbook.worksheets.add("Istruzioni");
  sheet.tabColor = COLORS.navy;
  title(sheet, "Validazione indipendente dei gold standard", `Valutatore ${code}`, "H");
  const rows = [
    ["Scopo", "Controllare in modo indipendente schema, dati di ground truth e query attese dei tre dataset."],
    ["Prima di iniziare", `Compilare e firmare Scheda_valutatore_${code}.docx. Verificare che il codice ${code} sia riportato anche nel foglio Profilo.`],
    ["Indipendenza", "Non consultare l'altro valutatore e non condividere giudizi o correzioni prima della consegna dei due file."],
    ["Materiali", "Per ogni dataset consultare README.md, prompt.txt, gold_schema.json, ground_truth.db, evaluation_spec.json e la cartella source."],
    ["Verdetto ACCETTA", "Il criterio è corretto e non richiede modifiche sostanziali."],
    ["Verdetto MODIFICA", "È necessaria una correzione. Compilare gravità, correzione proposta e motivazione/evidenza."],
    ["Verdetto INCERTO", "Le prove non consentono una decisione. Indicare quale chiarimento o verifica manca."],
    ["Gravità CRITICA", "Errore che rende non valido il gold standard o una query critica."],
    ["Gravità MAGGIORE", "Errore sostanziale ma circoscritto, con impatto su schema, dati o risultati attesi."],
    ["Gravità MINORE", "Correzione locale che non cambia le conclusioni principali."],
    ["Evidenza", "Citare file, tabella/colonna, query ID o record interessato. Non basarsi soltanto su preferenze stilistiche."],
    ["Consegna", `Restituire Valutazione_gold_standard_${code}.xlsx e la scheda DOCX firmata. Non rinominare il codice pseudonimo.`],
    ["Passo successivo", "Solo dopo entrambe le consegne, il coordinatore confronterà i disaccordi e organizzerà il consenso."],
  ];
  sheet.getRange("A4:B16").values = rows;
  sheet.getRange("A4:A16").format = {
    fill: COLORS.lightBlue,
    font: { name: "Arial", size: 10, bold: true, color: COLORS.navy },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "outside", style: "thin", color: COLORS.line },
  };
  sheet.getRange("B4:B16").format = {
    fill: "#FFFFFF",
    font: { name: "Arial", size: 10, color: COLORS.text },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "outside", style: "thin", color: COLORS.line },
  };
  sheet.getRange("A4:A16").format.columnWidth = 22;
  sheet.getRange("B4:B16").format.columnWidth = 92;
  sheet.getRange("A4:B16").format.autofitRows();
  styleBase(sheet, "A1:H18");
  return sheet;
}

function addProfile(workbook, code) {
  const sheet = workbook.worksheets.add("Profilo");
  sheet.tabColor = COLORS.blue;
  title(sheet, "Profilo del valutatore", "Compilare i campi gialli; la firma resta nella scheda DOCX.", "F");
  const values = [
    ["Campo", "Valore"],
    ["Codice pseudonimo", code],
    ["Titolo di studio", ""],
    ["Ruolo o esperienza pertinente", ""],
    ["Anni di esperienza con database", ""],
    ["Sintesi dell'esperienza con database", ""],
    ["Dichiarazione d'indipendenza", ""],
    ["Data di compilazione", null],
  ];
  sheet.getRange("A4:B11").values = values;
  styleHeader(sheet.getRange("A4:B4"));
  sheet.getRange("A5:A11").format = {
    fill: COLORS.lightBlue,
    font: { name: "Arial", size: 10, bold: true, color: COLORS.navy },
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.line },
  };
  styleInput(sheet.getRange("B5:B11"));
  sheet.getRange("B5").format.fill = COLORS.paleGray;
  sheet.getRange("B5").format.font = { name: "Arial", size: 10, bold: true, color: COLORS.navy };
  sheet.getRange("B10").dataValidation = { rule: { type: "list", values: ["CONFERMO", "NON CONFERMO"] } };
  sheet.getRange("B11").setNumberFormat("dd/mm/yyyy");
  sheet.getRange("A4:A11").format.columnWidth = 37;
  sheet.getRange("B4:B11").format.columnWidth = 70;
  sheet.getRange("A4:B11").format.wrapText = true;
  sheet.getRange("A4:B11").format.autofitRows();
  sheet.getRange("A13:F13").merge();
  sheet.getRange("A13").values = [["La scheda DOCX firmata costituisce la dichiarazione formale. Questo foglio mantiene il collegamento pseudonimizzato con la valutazione."]];
  sheet.getRange("A13:F13").format = { fill: COLORS.paleGray, font: { name: "Arial", size: 9, italic: true, color: COLORS.text }, wrapText: true, rowHeight: 32 };
  styleBase(sheet, "A1:F14");
  return sheet;
}

function reviewItems(dataset) {
  const p = dataset.prefix;
  return [
    [`${p}-S01`, "Schema", "gold_schema.json", "Normalizzazione", "Ogni tabella rispetta la terza forma normale in base alle dipendenze funzionali del dominio."],
    [`${p}-S02`, "Schema", "gold_schema.json", "Chiavi primarie", "Ogni tabella ha una chiave primaria corretta e sufficiente a identificare i record."],
    [`${p}-S03`, "Schema", "gold_schema.json", "Chiavi esterne", "Le chiavi esterne referenziano tabelle e colonne esistenti e modellano relazioni corrette."],
    [`${p}-S04`, "Schema", "gold_schema.json", "Cardinalità", "Le cardinalità e le tabelle associative riflettono il dominio descritto nelle fonti."],
    [`${p}-S05`, "Schema", "gold_schema.json", "Tipi di dato", "I tipi di dato sono adeguati ai valori e alle operazioni previste."],
    [`${p}-S06`, "Schema", "gold_schema.json", "Vincoli", "NOT NULL e UNIQUE sono applicati agli attributi semanticamente obbligatori o univoci."],
    [`${p}-S07`, "Schema", "gold_schema.json", "Nomi", "Tabelle e colonne hanno nomi chiari, coerenti e in snake_case."],
    [`${p}-D01`, "Dati", "ground_truth.db", "Integrità referenziale", "Il database di ground truth non contiene riferimenti orfani o violazioni dei vincoli dichiarati."],
    [`${p}-D02`, "Dati", "source/*; ground_truth.db", "Coerenza con le fonti", "I dati osservabili nel ground truth corrispondono ai documenti sorgente dopo la canonicalizzazione prevista."],
    [`${p}-D03`, "Dati", "evaluation_spec.json", "Ambito osservabile", "Le inclusioni e le esclusioni dall'ambito osservabile sono motivate e coerenti con le fonti consegnate al sistema."],
    [`${p}-D04`, "Dati", "evaluation_spec.json", "Chiavi naturali", "Le chiavi naturali consentono un allineamento stabile senza dipendere da identificatori sintetici."],
    [`${p}-D05`, "Dati", "ground_truth.db", "Copertura", "Entità e fatti necessari alle query attese sono presenti senza record critici mancanti o estranei."],
    [`${p}-C01`, "Decisione", "tutti", "Validità complessiva", "Il gold standard del dataset può essere usato come riferimento dopo le eventuali correzioni indicate."],
  ];
}

function addDatasetSheet(workbook, dataset) {
  const sheet = workbook.worksheets.add(dataset.label);
  title(sheet, `Revisione ${dataset.label}`, "Schema, dati e ambito osservabile", "J");
  const headers = [["Item ID", "Area", "Artefatto", "Oggetto", "Criterio da verificare", "Verdetto", "Gravità", "Correzione proposta", "Motivazione / evidenza", "Note"]];
  const rows = reviewItems(dataset).map((x) => [...x, "", "", "", "", ""]);
  sheet.getRange(`A4:J${4 + rows.length}`).values = [...headers, ...rows];
  styleHeader(sheet.getRange("A4:J4"));
  const endRow = 4 + rows.length;
  sheet.getRange(`A5:E${endRow}`).format.fill = "#FFFFFF";
  sheet.getRange(`A5:J${endRow}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  sheet.getRange(`A5:J${endRow}`).format.wrapText = true;
  sheet.getRange(`A5:J${endRow}`).format.verticalAlignment = "top";
  addReviewFormatting(sheet, 5, endRow, "F", "G", "F", "J");
  const widths = [12, 13, 23, 20, 58, 14, 14, 42, 48, 34];
  widths.forEach((w, i) => sheet.getRangeByIndexes(0, i, endRow, 1).format.columnWidth = w);
  sheet.getRange(`A5:J${endRow}`).format.autofitRows();
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(1);
  styleBase(sheet, `A1:J${endRow}`);
  return { sheet, endRow };
}

async function addQueries(workbook, specs) {
  const sheet = workbook.worksheets.add("Query");
  title(sheet, "Revisione delle query attese", "Controllare scopo, SQL, criticità e modalità di confronto.", "L");
  const headers = [["Dataset", "Query ID", "Critica", "Descrizione", "SQL atteso", "Confronto", "Verdetto", "Gravità", "Correzione proposta", "Motivazione / evidenza", "Note", "File sorgente"]];
  const rows = [];
  for (const dataset of DATASETS) {
    const spec = specs[dataset.key];
    for (const q of spec.functional_queries) {
      rows.push([
        dataset.key,
        q.id,
        q.critical ? "SI" : "NO",
        q.description,
        q.sql,
        `${q.comparison.mode}: ${q.comparison.columns.join(", ")}`,
        "", "", "", "", "",
        `${dataset.key}/evaluation_spec.json`,
      ]);
    }
  }
  const endRow = 4 + rows.length;
  sheet.getRange(`A4:L${endRow}`).values = [...headers, ...rows];
  styleHeader(sheet.getRange("A4:L4"));
  sheet.getRange(`A5:F${endRow}`).format.fill = "#FFFFFF";
  sheet.getRange(`G5:K${endRow}`).format.fill = COLORS.paleYellow;
  sheet.getRange(`L5:L${endRow}`).format.fill = COLORS.paleGray;
  sheet.getRange(`A5:L${endRow}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  sheet.getRange(`A5:L${endRow}`).format.wrapText = true;
  sheet.getRange(`A5:L${endRow}`).format.verticalAlignment = "top";
  addReviewFormatting(sheet, 5, endRow, "G", "H", "G", "K");
  const widths = [14, 11, 10, 43, 84, 34, 14, 14, 42, 46, 30, 28];
  widths.forEach((w, i) => sheet.getRangeByIndexes(0, i, endRow, 1).format.columnWidth = w);
  sheet.getRange(`A5:L${endRow}`).format.autofitRows();
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(2);
  styleBase(sheet, `A1:L${endRow}`);
  return { sheet, endRow };
}

function addSummary(workbook, datasetEnds, queryEnd) {
  const sheet = workbook.worksheets.add("Riepilogo");
  sheet.tabColor = COLORS.navy;
  title(sheet, "Riepilogo della revisione", "Aggiornato automaticamente dai verdetti inseriti.", "H");
  sheet.getRange("A4:F4").values = [["Sezione", "Item totali", "Compilati", "Da completare", "Modifiche", "Incerti"]];
  styleHeader(sheet.getRange("A4:F4"));
  const sections = [
    ["University", "University", 5, datasetEnds.University, "F"],
    ["Library", "Library", 5, datasetEnds.Library, "F"],
    ["Hospital", "Hospital", 5, datasetEnds.Hospital, "F"],
    ["Query", "Query", 5, queryEnd, "G"],
  ];
  sections.forEach((s, idx) => {
    const row = 5 + idx;
    const [label, tab, start, end, verdictCol] = s;
    sheet.getRange(`A${row}`).values = [[label]];
    sheet.getRange(`B${row}`).formulas = [[`=ROWS('${tab}'!${verdictCol}${start}:${verdictCol}${end})`]];
    sheet.getRange(`C${row}`).formulas = [[`=B${row}-COUNTBLANK('${tab}'!${verdictCol}${start}:${verdictCol}${end})`]];
    sheet.getRange(`D${row}`).formulas = [[`=COUNTBLANK('${tab}'!${verdictCol}${start}:${verdictCol}${end})`]];
    sheet.getRange(`E${row}`).formulas = [[`=COUNTIFS('${tab}'!${verdictCol}${start}:${verdictCol}${end},"MODIFICA")`]];
    sheet.getRange(`F${row}`).formulas = [[`=COUNTIFS('${tab}'!${verdictCol}${start}:${verdictCol}${end},"INCERTO")`]];
  });
  sheet.getRange("A9:F9").values = [["Totale", null, null, null, null, null]];
  for (const col of ["B", "C", "D", "E", "F"]) sheet.getRange(`${col}9`).formulas = [[`=SUM(${col}5:${col}8)`]];
  sheet.getRange("A9:F9").format = { fill: COLORS.lightBlue, font: { name: "Arial", size: 10, bold: true, color: COLORS.navy }, borders: { preset: "doubleBottom", style: "thin", color: COLORS.blue } };
  sheet.getRange("A11:B15").values = [
    ["Controllo", "Stato"],
    ["Profilo: titolo di studio", null],
    ["Profilo: esperienza database", null],
    ["Profilo: indipendenza", null],
    ["Valutazioni", null],
  ];
  styleHeader(sheet.getRange("A11:B11"));
  sheet.getRange("B12").formulas = [[`=IF(Profilo!B6="","DA COMPLETARE","OK")`]];
  sheet.getRange("B13").formulas = [[`=IF(OR(Profilo!B8="",Profilo!B9=""),"DA COMPLETARE","OK")`]];
  sheet.getRange("B14").formulas = [[`=IF(Profilo!B10="CONFERMO","OK","DA VERIFICARE")`]];
  sheet.getRange("B15").formulas = [[`=IF(D9=0,"COMPLETE","DA COMPLETARE")`]];
  sheet.getRange("A12:A15").format = { fill: COLORS.lightBlue, font: { name: "Arial", size: 10, bold: true, color: COLORS.navy }, borders: { preset: "outside", style: "thin", color: COLORS.line } };
  sheet.getRange("B12:B15").format = { fill: "#FFFFFF", borders: { preset: "outside", style: "thin", color: COLORS.line } };
  sheet.getRange("B12:B15").conditionalFormats.add("containsText", { text: "OK", format: { fill: COLORS.paleGreen, font: { bold: true, color: "#375623" } } });
  sheet.getRange("B12:B15").conditionalFormats.add("containsText", { text: "DA", format: { fill: COLORS.paleRed, font: { bold: true, color: "#9C0006" } } });
  sheet.getRange("A4:A15").format.columnWidth = 32;
  sheet.getRange("B4:F15").format.columnWidth = 17;
  sheet.getRange("A4:F15").format.horizontalAlignment = "center";
  sheet.getRange("A4:F15").format.autofitRows();
  sheet.getRange("A17:H18").merge();
  sheet.getRange("A17").values = [["Questo riepilogo controlla soltanto la completezza del file Excel. La validazione formale richiede anche la scheda DOCX firmata. Non avviare il confronto con l'altro valutatore prima della consegna indipendente di entrambi."]];
  sheet.getRange("A17:H18").format = { fill: COLORS.paleGray, font: { name: "Arial", size: 9, italic: true, color: COLORS.text }, wrapText: true, verticalAlignment: "center" };
  styleBase(sheet, "A1:H18");
  return sheet;
}

async function readSpecs() {
  const specs = {};
  for (const dataset of DATASETS) {
    specs[dataset.key] = JSON.parse(await fs.readFile(path.join(datasetsDir, dataset.key, "evaluation_spec.json"), "utf8"));
  }
  return specs;
}

async function buildWorkbook(code, specs) {
  const workbook = Workbook.create();
  const instructions = addInstructions(workbook, code);
  addProfile(workbook, code);
  const datasetEnds = {};
  for (const dataset of DATASETS) {
    const result = addDatasetSheet(workbook, dataset);
    datasetEnds[dataset.label] = result.endRow;
  }
  const query = await addQueries(workbook, specs);
  addSummary(workbook, datasetEnds, query.endRow);

  workbook.recalculate();
  const keyCheck = await workbook.inspect({
    kind: "table",
    range: "Riepilogo!A4:F15",
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 8,
    maxChars: 8000,
  });
  console.log(`${code} summary inspection\n${keyCheck.ndjson}`);
  const errorCheck = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 100 },
    summary: `${code} final formula error scan`,
  });
  console.log(`${code} formula scan\n${errorCheck.ndjson}`);

  await fs.mkdir(path.join(previewDir, code), { recursive: true });
  for (const sheetName of ["Istruzioni", "Profilo", "University", "Library", "Hospital", "Query", "Riepilogo"]) {
    const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, code, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
  const out = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(outputDir, `Valutazione_gold_standard_${code}.xlsx`);
  await out.save(outputPath);
  console.log(outputPath);
}

await fs.mkdir(outputDir, { recursive: true });
const specs = await readSpecs();
for (const code of ["GOLD-A", "GOLD-B"]) await buildWorkbook(code, specs);
