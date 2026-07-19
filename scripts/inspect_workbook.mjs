import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


const [inputPath, outputPath] = process.argv.slice(2);

if (inputPath === undefined || outputPath === undefined) {
  throw new Error("Usage: node inspect_workbook.mjs <input.xlsx> <output.json>");
}

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const summary = await workbook.inspect({
  kind: "workbook,sheet,table,region",
  include: "id,name,values,formulas",
  maxChars: 30000,
  tableMaxRows: 12,
  tableMaxCols: 20,
  tableMaxCellChars: 200,
});
const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 10000,
});
const referenceDefinitions = workbook.worksheets
  .getItem("Reference-Variables&Definitions")
  .getRange("A1:C2334").values;
const convertedVariables = workbook.worksheets
  .getItem("Converted Variables")
  .getRange("A1:H87").values;
const performanceRatios = workbook.worksheets
  .getItem("Performance & Condition Ratios")
  .getRange("A1:B40").values;
const demographics = workbook.worksheets
  .getItem("Demographics")
  .getRange("A1:B38").values;
const payload = {
  input: path.basename(inputPath),
  summary: summary.ndjson,
  sheets: sheets.ndjson,
  referenceDefinitions,
  convertedVariables,
  performanceRatios,
  demographics,
};

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, JSON.stringify(payload, null, 2), "utf8");
console.log(outputPath);
