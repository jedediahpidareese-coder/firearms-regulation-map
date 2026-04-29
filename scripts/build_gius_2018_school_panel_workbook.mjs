import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const processedDir = path.join(root, "data", "processed");
const outputDir = path.join(root, "outputs");
const outputPath = path.join(outputDir, "gius_2018_school_shootings_replication.xlsx");

function csvToMatrix(csvText) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;
  for (let i = 0; i < csvText.length; i += 1) {
    const char = csvText[i];
    const next = csvText[i + 1];
    if (inQuotes) {
      if (char === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        value += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(value);
      value = "";
    } else if (char === "\n") {
      row.push(value.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }
  if (value.length > 0 || row.length > 0) {
    row.push(value.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows.filter((entry) => !(entry.length === 1 && entry[0] === ""));
}

function parseCell(raw) {
  if (raw === "") return null;
  if (/^-?\d+(\.\d+)?$/.test(raw)) return Number(raw);
  return raw;
}

async function readCsv(name) {
  const text = await fs.readFile(path.join(processedDir, name), "utf8");
  const rows = csvToMatrix(text);
  return rows.map((row) => row.map(parseCell));
}

async function readJson(name) {
  const text = await fs.readFile(path.join(processedDir, name), "utf8");
  return JSON.parse(text);
}

function autoWidth(data, maxCols = 40) {
  const widths = [];
  const cols = Math.min(maxCols, data[0]?.length ?? 0);
  for (let c = 0; c < cols; c += 1) {
    let maxLen = 10;
    for (let r = 0; r < data.length; r += 1) {
      const cell = data[r][c];
      const len = cell == null ? 0 : String(cell).length;
      if (len > maxLen) maxLen = len;
    }
    widths.push(Math.min(Math.max(maxLen * 7 + 18, 72), 280));
  }
  return widths;
}

function applyColumnWidths(sheet, data, maxCols = 40) {
  const widths = autoWidth(data, maxCols);
  widths.forEach((width, idx) => {
    sheet.getRangeByIndexes(0, idx, Math.max(data.length, 1), 1).format.columnWidthPx = width;
  });
}

async function addDataSheet(workbook, sheetName, csvName, title, subtitle, options = {}) {
  const data = await readCsv(csvName);
  const sheet = workbook.worksheets.add(sheetName);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A1").format.font = { bold: true, size: 18, color: "#153B5B" };
  sheet.getRange("A2").format.font = { italic: true, color: "#475467" };

  const startRow = 3;
  const rowCount = data.length;
  const colCount = data[0].length;
  sheet.getRangeByIndexes(startRow, 0, rowCount, colCount).values = data;
  sheet.getRangeByIndexes(startRow, 0, 1, colCount).format.fill = { color: "#DDEBF7" };
  sheet.getRangeByIndexes(startRow, 0, 1, colCount).format.font = { bold: true, color: "#12325A" };
  if (rowCount > 1) {
    sheet.getRangeByIndexes(startRow + 1, 0, rowCount - 1, colCount).format.font = { size: 10 };
  }
  sheet.getRangeByIndexes(startRow, 0, rowCount, colCount).format.wrapText = false;
  sheet.freezePanes.freezeRows(startRow + 1);
  sheet.freezePanes.freezeColumns(Math.min(options.freezeColumns ?? 3, colCount));
  applyColumnWidths(sheet, data, options.maxColsForWidth ?? Math.min(colCount, 28));
  return { sheet, data, startRow, rowCount, colCount };
}

async function main() {
  const workbook = Workbook.create();
  const summary = await readJson("gius_2018_panel_summary.json");
  const annualTargets = await readCsv("gius_2018_annual_targets_1990_2014.csv");

  const dashboard = workbook.worksheets.add("Dashboard");
  dashboard.getRange("A1").values = [["Gius (2018) School Shootings Reconstruction"]];
  dashboard.getRange("A2").values = [[
    "Balanced 50-state panel for 1990-2014. The state-year distribution is reconstructed from cited source files and calibrated so annual national killed and wounded totals match the paper's figures exactly.",
  ]];
  dashboard.getRange("A1").format.font = { bold: true, size: 20, color: "#12325A" };
  dashboard.getRange("A2").format.font = { italic: true, color: "#475467" };
  dashboard.getRange("A2:H2").format.wrapText = true;

  const summaryTable = [
    ["Metric", "Value", "Detail"],
    ["Rows", summary.rows, "Expected 50 states x 25 years"],
    ["States", summary.states, "Balanced 50-state panel"],
    ["Years", `${summary.years[0]}-${summary.years[1]}`, "Paper sample window"],
    ["Paper fatalities", summary.paper_total_killed, "Exact total from Figures 1 and 2"],
    ["Paper injuries", summary.paper_total_wounded, "Exact total from Figures 1 and 2"],
    ["Paper victims", summary.paper_total_victims, "Fatalities + injuries"],
    ["Raw victims before calibration", summary.raw_total_killed + summary.raw_total_wounded, "From reconstructed source distribution"],
    ["Calibrated victims", summary.calibrated_total_victims, "Matches the paper exactly"],
  ];
  dashboard.getRange("A4:C12").values = summaryTable;
  dashboard.getRange("A4:C4").format.fill = { color: "#DDEBF7" };
  dashboard.getRange("A4:C4").format.font = { bold: true, color: "#12325A" };
  dashboard.getRange("A4:C12").format.borders = { style: "thin", color: "#C8D4E3" };

  dashboard.getRange("E4").values = [["Exact components"]];
  dashboard.getRange("E4").format.font = { bold: true, size: 13, color: "#12325A" };
  const exactItems = summary.exact_vs_approx.exact.map((item) => [item]);
  dashboard.getRangeByIndexes(4, 4, exactItems.length, 1).values = exactItems;
  dashboard.getRangeByIndexes(4, 4, exactItems.length, 1).format.wrapText = true;
  dashboard.getRangeByIndexes(4, 4, exactItems.length, 1).format.font = { size: 10 };

  dashboard.getRange("G4").values = [["Approximate components"]];
  dashboard.getRange("G4").format.font = { bold: true, size: 13, color: "#8A4B08" };
  const approxItems = summary.exact_vs_approx.approximate.map((item) => [item]);
  dashboard.getRangeByIndexes(4, 6, approxItems.length, 1).values = approxItems;
  dashboard.getRangeByIndexes(4, 6, approxItems.length, 1).format.wrapText = true;
  dashboard.getRangeByIndexes(4, 6, approxItems.length, 1).format.font = { size: 10 };

  dashboard.getRange("A15:J41").values = annualTargets;
  dashboard.getRange("A15:J15").format.fill = { color: "#E9F1E7" };
  dashboard.getRange("A15:J15").format.font = { bold: true, color: "#163A1A" };
  dashboard.getRange("A15:J41").format.borders = { style: "thin", color: "#C8D8C6" };

  try {
    const chart = dashboard.charts.add("line", {
      topLeft: { row: 3, col: 9 },
      widthPx: 760,
      heightPx: 340,
    });
    chart.title.text = "Annual School Shooting Victims: Paper vs Raw Build";
    chart.legend.position = "bottom";
    chart.categoryAxis.title.text = "Year";
    chart.valueAxis.title.text = "Victims";
    chart.series.add({
      name: "Paper victims target",
      categories: "Dashboard!A16:A40",
      values: "Dashboard!D16:D40",
    });
    chart.series.add({
      name: "Raw victims total",
      categories: "Dashboard!A16:A40",
      values: "Dashboard!G16:G40",
    });
    chart.series.add({
      name: "Calibrated victims total",
      categories: "Dashboard!A16:A40",
      values: "Dashboard!J16:J40",
    });
  } catch (error) {
    dashboard.getRange("J15").values = [[`Chart fallback: ${String(error).slice(0, 120)}`]];
    dashboard.getRange("J15").format.font = { italic: true, color: "#8A1C1C" };
  }

  applyColumnWidths(dashboard, summaryTable, 3);
  dashboard.getRange("C:C").format.columnWidthPx = 220;
  dashboard.getRange("E:E").format.columnWidthPx = 300;
  dashboard.getRange("G:G").format.columnWidthPx = 320;
  dashboard.freezePanes.freezeRows(3);

  await addDataSheet(
    workbook,
    "panel_gius_2018",
    "gius_2018_school_panel_1990_2014.csv",
    "Main Gius 2018 Reconstruction Panel",
    "Balanced 50-state, 1990-2014 panel for school-shootings replication work.",
    { freezeColumns: 4, maxColsForWidth: 20 },
  );

  await addDataSheet(
    workbook,
    "annual_targets",
    "gius_2018_annual_targets_1990_2014.csv",
    "Annual Paper Targets",
    "Exact yearly fatalities and injuries read from the paper's figures, alongside raw and calibrated totals.",
    { freezeColumns: 2, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "raw_state_year",
    "gius_2018_school_outcomes_raw_state_year_1990_2014.csv",
    "Raw State-Year Outcomes",
    "Pre-calibration state-year outcomes implied by the reconstructed source distribution.",
    { freezeColumns: 3, maxColsForWidth: 10 },
  );

  await addDataSheet(
    workbook,
    "incidents_prelim",
    "gius_2018_school_incidents_preliminary_1990_2014.csv",
    "Preliminary Incident File",
    "Event-level source build before annual calibration. This sheet is for audit and reconstruction transparency.",
    { freezeColumns: 4, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "variables",
    "gius_2018_variable_dictionary.csv",
    "Variable Dictionary",
    "Definitions for the main outcome, law, and control variables included in the replication panel.",
    { freezeColumns: 1, maxColsForWidth: 5 },
  );

  await addDataSheet(
    workbook,
    "source_notes",
    "gius_2018_source_notes.csv",
    "Source Notes",
    "Exact versus approximate components are documented here so the reconstruction can be audited quickly.",
    { freezeColumns: 1, maxColsForWidth: 5 },
  );

  await addDataSheet(
    workbook,
    "balance_checks",
    "gius_2018_balance_checks.csv",
    "Balance Checks",
    "Panel-level checks for row count, duplicate state-years, missing required cells, and annual target matching.",
    { freezeColumns: 1, maxColsForWidth: 6 },
  );

  await fs.mkdir(outputDir, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(outputPath);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
