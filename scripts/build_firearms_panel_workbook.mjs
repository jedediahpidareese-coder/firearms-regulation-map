import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const processedDir = path.join(root, "data", "processed");
const outputDir = path.join(root, "outputs");
const outputPath = path.join(outputDir, "firearms_regulation_balanced_panel.xlsx");

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
  return rows.filter((r) => !(r.length === 1 && r[0] === ""));
}

function parseCell(raw) {
  if (raw === "") return null;
  if (/^-?\d+(\.\d+)?$/.test(raw)) return Number(raw);
  return raw;
}

async function readCsv(name) {
  const text = await fs.readFile(path.join(processedDir, name), "utf8");
  const rows = csvToMatrix(text);
  return rows.map((r) => r.map(parseCell));
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
    widths.push(Math.min(Math.max(maxLen * 7 + 16, 72), 260));
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
  sheet.getRangeByIndexes(0, 0, 1, 1).format.font = { bold: true, size: 18, color: "#14315C" };
  sheet.getRangeByIndexes(1, 0, 1, 1).format.font = { italic: true, color: "#475467" };
  const startRow = 3;
  const rowCount = data.length;
  const colCount = data[0].length;
  sheet.getRangeByIndexes(startRow, 0, rowCount, colCount).values = data;
  sheet.getRangeByIndexes(startRow, 0, 1, colCount).format.fill = { color: "#DCE8F7" };
  sheet.getRangeByIndexes(startRow, 0, 1, colCount).format.font = { bold: true, color: "#12233D" };
  sheet.getRangeByIndexes(startRow + 1, 0, rowCount - 1, colCount).format.font = { size: 10 };
  sheet.freezePanes.freezeRows(startRow + 1);
  sheet.freezePanes.freezeColumns(Math.min(options.freezeColumns ?? 3, colCount));
  sheet.getRangeByIndexes(startRow, 0, rowCount, colCount).format.wrapText = false;
  applyColumnWidths(sheet, data, options.maxColsForWidth ?? Math.min(colCount, 30));
  return { sheet, data, startRow, rowCount, colCount };
}

async function main() {
  const workbook = Workbook.create();

  const panelSummary = await readCsv("panel_summary.csv");
  const dashboardTrends = await readCsv("dashboard_trends.csv");
  const summaryEndRow = 4 + panelSummary.length - 1;
  const trendEndRow = 10 + dashboardTrends.length - 1;

  const dashboard = workbook.worksheets.add("Dashboard");
  dashboard.getRange("A1").values = [["Firearms Regulation and Crime: Balanced State-Year Panels"]];
  dashboard.getRange("A2").values = [[
    "Balanced panels restricted to the 50 states. The latest fully balanced annual panel ends in 2024 because firearm-law and violent/property crime series do not yet overlap through 2025-2026. A long-run demographic panel now extends race, Hispanic origin, sex, age, income, poverty, and education controls back to 1990.",
  ]];
  dashboard.getRange("A1").format.font = { bold: true, size: 20, color: "#12325A" };
  dashboard.getRange("A2").format.font = { italic: true, color: "#475467" };
  dashboard.getRange(`A4:G${summaryEndRow}`).values = panelSummary;
  dashboard.getRange("A4:G4").format.fill = { color: "#DCE8F7" };
  dashboard.getRange("A4:G4").format.font = { bold: true, color: "#12233D" };
  dashboard.getRange(`A4:G${summaryEndRow}`).format.font = { size: 10 };
  dashboard.getRange(`A10:F${trendEndRow}`).values = dashboardTrends;
  dashboard.getRange("A10:F10").format.fill = { color: "#E7F0E8" };
  dashboard.getRange("A10:F10").format.font = { bold: true, color: "#143B20" };
  dashboard.getRange("H4").values = [["Recommended usage"]];
  dashboard.getRange("H4").format.font = { bold: true, size: 14, color: "#12325A" };
  dashboard.getRange("H5").values = [[
    "panel_core_1979_2024: long-run laws + crime + unemployment + real per-capita income.",
  ]];
  dashboard.getRange("H6").values = [[
    "panel_demographic_1990_2024: adds long-run Census/SAIPE demographics and interpolated education.",
  ]];
  dashboard.getRange("H7").values = [[
    "panel_market_1999_2024: adds annual NICS firearm background check measures.",
  ]];
  dashboard.getRange("H8").values = [[
    "panel_modern_2008_2024: exact ACS demographic and socioeconomic covariates plus NICS.",
  ]];
  dashboard.getRange("H9").values = [[
    "current_partial_2025_2026: supplemental partial-current indicators, not a balanced panel.",
  ]];
  dashboard.getRange("H5:H9").format.wrapText = true;
  dashboard.getRange("H5:H9").format.font = { size: 10 };

  try {
    const chart = dashboard.charts.add("line", {
      topLeft: { row: 11, col: 7 },
      widthPx: 720,
      heightPx: 360,
    });
    chart.title.text = "Mean State Crime Rates Over Time";
    chart.legend.position = "bottom";
    chart.categoryAxis.title.text = "Year";
    chart.valueAxis.title.text = "Rate per 100,000";
    chart.series.add({
      name: "Mean violent rate",
      categories: `Dashboard!A11:A${trendEndRow}`,
      values: `Dashboard!B11:B${trendEndRow}`,
    });
    chart.series.add({
      name: "Mean property rate",
      categories: `Dashboard!A11:A${trendEndRow}`,
      values: `Dashboard!C11:C${trendEndRow}`,
    });
  } catch (error) {
    dashboard.getRange("H10").values = [[`Chart generation fallback: ${String(error).slice(0, 120)}`]];
    dashboard.getRange("H10").format.font = { italic: true, color: "#8A1C1C" };
  }

  dashboard.freezePanes.freezeRows(3);
  applyColumnWidths(dashboard, panelSummary, 8);
  dashboard.getRange("A2:J2").format.wrapText = true;
  dashboard.getRange(`A4:G${summaryEndRow}`).format.borders = { style: "thin", color: "#B5C2D1" };
  dashboard.getRange(`A10:F${trendEndRow}`).format.borders = { style: "thin", color: "#C6D4C9" };
  dashboard.getRange("H5:H9").format.columnWidthPx = 420;

  await addDataSheet(
    workbook,
    "panel_core",
    "panel_core_1979_2024.csv",
    "Balanced Core Panel",
    "1979-2024, 50 states. Tufts firearm laws + violent/property crime + unemployment + real per-capita income.",
    { freezeColumns: 4, maxColsForWidth: 24 },
  );

  await addDataSheet(
    workbook,
    "panel_demographic",
    "panel_demographic_1990_2024.csv",
    "Balanced Long-Run Demographic Panel",
    "1990-2024, 50 states. Core panel plus historical Census race / sex / age shares, SAIPE income and poverty, and interpolated education.",
    { freezeColumns: 4, maxColsForWidth: 30 },
  );

  await addDataSheet(
    workbook,
    "panel_market",
    "panel_market_1999_2024.csv",
    "Balanced Firearm-Market Panel",
    "1999-2024, 50 states. Core panel plus annual NICS background-check measures.",
    { freezeColumns: 4, maxColsForWidth: 28 },
  );

  await addDataSheet(
    workbook,
    "panel_modern",
    "panel_modern_2008_2024.csv",
    "Balanced Modern Demographic Panel",
    "2008-2024, 50 states. Market panel plus exact ACS demographic and socioeconomic controls.",
    { freezeColumns: 4, maxColsForWidth: 32 },
  );

  await addDataSheet(
    workbook,
    "demographics_long",
    "historical_demographics_1990_2024.csv",
    "Long-Run Demographic Controls",
    "1990-2024, 50 states. Clean historical demographic and socioeconomic controls before joining to the core crime/law panel.",
    { freezeColumns: 4, maxColsForWidth: 18 },
  );

  await addDataSheet(
    workbook,
    "crime_clean",
    "crime_state_clean_1979_2024.csv",
    "Clean State Crime Series",
    "1979-2024, 50 states. Violent and property crime counts and rates with a common annual population denominator.",
    { freezeColumns: 3, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "current_partial",
    "current_partial_2025_2026.csv",
    "Partial Current Indicators",
    "Supplemental non-balanced state indicators using the latest NICS and unemployment updates available during the build.",
    { freezeColumns: 2, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "coverage",
    "coverage_diagnostics.csv",
    "Coverage Diagnostics",
    "Counts of complete states by year for each required variable bundle, used to identify the balanced windows.",
    { freezeColumns: 2, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "balance_checks",
    "panel_balance_checks.csv",
    "Balance Checks",
    "Panel-level balance validation including row counts, distinct states, distinct years, duplicates, and missing required cells.",
    { freezeColumns: 1, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "repairs",
    "crime_repairs_log.csv",
    "Crime Repair Log",
    "Documented source correction applied before panel construction.",
    { freezeColumns: 2, maxColsForWidth: 12 },
  );

  await addDataSheet(
    workbook,
    "variables",
    "variable_dictionary.csv",
    "Variable Dictionary",
    "Law variables come from the Tufts codebook; non-law variables were documented during the build.",
    { freezeColumns: 1, maxColsForWidth: 5 },
  );

  await addDataSheet(
    workbook,
    "sources",
    "sources_integrated.csv",
    "Integrated Sources",
    "Only sources actually merged into the workbook panels are listed here.",
    { freezeColumns: 1, maxColsForWidth: 5 },
  );

  await addDataSheet(
    workbook,
    "demographic_notes",
    "historical_demographic_notes.csv",
    "Historical Demographic Notes",
    "Source and interpolation notes for the long-run demographic panel.",
    { freezeColumns: 1, maxColsForWidth: 5 },
  );

  await addDataSheet(
    workbook,
    "law_highlights",
    "highlight_law_variables.csv",
    "Law Variable Highlights",
    "A short list of especially relevant firearm-law indicators for RTC / permitless carry / ERPO / magazine-ban style work.",
    { freezeColumns: 1, maxColsForWidth: 4 },
  );

  const summaryInspect = await workbook.inspect({
    kind: "table",
    range: "Dashboard!A1:J20",
    include: "values",
    tableMaxRows: 20,
    tableMaxCols: 10,
  });
  console.log(summaryInspect.ndjson);

  const errorScan = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "final formula error scan",
  });
  console.log(errorScan.ndjson);

  const renderTargets = [
    { sheetName: "Dashboard", range: "A1:J20" },
    { sheetName: "panel_core", range: "A1:L14" },
    { sheetName: "panel_demographic", range: "A1:L14" },
    { sheetName: "panel_market", range: "A1:L14" },
    { sheetName: "panel_modern", range: "A1:L14" },
    { sheetName: "demographics_long", range: "A1:L14" },
    { sheetName: "crime_clean", range: "A1:H14" },
    { sheetName: "current_partial", range: "A1:H14" },
    { sheetName: "coverage", range: "A1:H14" },
    { sheetName: "balance_checks", range: "A1:L10" },
    { sheetName: "repairs", range: "A1:F10" },
    { sheetName: "variables", range: "A1:E14" },
    { sheetName: "sources", range: "A1:E14" },
    { sheetName: "demographic_notes", range: "A1:E10" },
    { sheetName: "law_highlights", range: "A1:B14" },
  ];
  for (const target of renderTargets) {
    await workbook.render({ ...target, scale: 1.2 });
  }

  await fs.mkdir(outputDir, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(JSON.stringify({ outputPath }));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
