/* Interactive choropleth: U.S. firearm regulation, ownership, crime, suicides, demographics.
 *
 * Loads:
 *   data/manifest.json   - high-level UI manifest (categories, defaults, year range)
 *   data/metadata.json   - per-variable definitions, sources, caveats
 *   data/panel.json      - per-state per-year values
 *
 * The states topology is fetched from a CDN copy of us-atlas (states-10m).
 */

const TOPO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

// FIPS -> postal abbreviation. The us-atlas topology keys states by 2-digit FIPS string.
const FIPS_TO_ABBR = {
  "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE",
  "11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA",
  "20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN",
  "28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM",
  "36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI",
  "45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA",
  "54":"WV","55":"WI","56":"WY"
};

const STATE_NAMES = {
  "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
  "CT":"Connecticut","DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia",
  "HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas",
  "KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts",
  "MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana",
  "NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico",
  "NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
  "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
  "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
  "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"
};

// Color schemes per category - keep distinct, colorblind-safe sequential palettes.
const CATEGORY_PALETTE = {
  "Regulation":              d3.interpolateBlues,
  "Crime":                   d3.interpolateOrRd,
  "Suicide & firearm deaths":d3.interpolatePuRd,
  "Gun ownership":           d3.interpolateGreens,
  "Demographics":            d3.interpolateViridis,
  "Economy":                 d3.interpolateYlGnBu,
};

const BINARY_COLORS = ["#dadad6", "#1f3a5f"]; // 0 = neutral gray, 1 = accent

// State of the page.
const state = {
  manifest: null,
  metadata: null,
  panel: null,
  topology: null,
  variable: null,
  year: null,
  hoveredAbbr: null,
  playing: false,
  playTimer: null,
};

const fmtAuto = d3.format(",.2~f");
const fmtPercent = d3.format(".1%");
const fmtInt = d3.format(",");

function formatValue(val, meta) {
  if (val == null || Number.isNaN(val)) return "no data";
  if (meta && meta.unit && meta.unit.startsWith("share")) return fmtPercent(val);
  if (meta && meta.unit === "USD") return "$" + fmtInt(Math.round(val));
  if (meta && meta.unit === "people") return fmtInt(Math.round(val));
  if (meta && meta.unit === "0/1") return val == 1 ? "Yes (1)" : "No (0)";
  if (Math.abs(val) >= 100) return fmtInt(Math.round(val));
  return fmtAuto(val);
}

async function loadAll() {
  const [manifest, metadata, panel, topology] = await Promise.all([
    d3.json("data/manifest.json"),
    d3.json("data/metadata.json"),
    d3.json("data/panel.json"),
    d3.json(TOPO_URL),
  ]);
  state.manifest = manifest;
  state.metadata = metadata;
  state.panel = panel;
  state.topology = topology;
}

function populateSelectors() {
  const catSel = document.getElementById("category-select");
  const varSel = document.getElementById("variable-select");
  const cats = Object.keys(state.manifest.categories);
  cats.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c; opt.textContent = c;
    catSel.appendChild(opt);
  });
  const defaultMeta = state.metadata[state.manifest.default_variable];
  catSel.value = defaultMeta.category;

  function refreshVarSelect() {
    varSel.innerHTML = "";
    const vars = state.manifest.categories[catSel.value];
    vars.forEach(v => {
      const meta = state.metadata[v];
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = meta.label;
      varSel.appendChild(opt);
    });
    varSel.value = vars.includes(state.variable) ? state.variable : vars[0];
    state.variable = varSel.value;
    clampYearToVariable();
    render();
  }
  catSel.addEventListener("change", refreshVarSelect);
  varSel.addEventListener("change", () => {
    state.variable = varSel.value;
    clampYearToVariable();
    render();
  });

  state.variable = state.manifest.default_variable;
  refreshVarSelect();
  varSel.value = state.variable;

  // Year slider.
  const slider = document.getElementById("year-slider");
  const [yMin, yMax] = state.manifest.year_range;
  slider.min = yMin; slider.max = yMax;
  slider.value = state.manifest.default_year;
  state.year = +slider.value;
  document.getElementById("year-min").textContent = yMin;
  document.getElementById("year-max").textContent = yMax;
  slider.addEventListener("input", () => {
    state.year = +slider.value;
    render();
  });

  // Play / pause.
  document.getElementById("play-button").addEventListener("click", togglePlay);

  // Generated timestamp.
  document.getElementById("generated-at").textContent =
    state.manifest.generated_at.replace("T", " ").replace("Z", " UTC");
}

function clampYearToVariable() {
  const meta = state.metadata[state.variable];
  if (!meta || !meta.observed_year_range) return;
  const [vMin, vMax] = meta.observed_year_range;
  const slider = document.getElementById("year-slider");
  if (state.year < vMin) state.year = vMin;
  if (state.year > vMax) state.year = vMax;
  slider.value = state.year;
}

function togglePlay() {
  const btn = document.getElementById("play-button");
  if (state.playing) {
    clearInterval(state.playTimer);
    state.playing = false;
    btn.classList.remove("playing");
    btn.innerHTML = "&#9654;";
  } else {
    state.playing = true;
    btn.classList.add("playing");
    btn.innerHTML = "&#9632;";
    const meta = state.metadata[state.variable];
    const [vMin, vMax] = meta.observed_year_range || state.manifest.year_range;
    state.playTimer = setInterval(() => {
      state.year = state.year >= vMax ? vMin : state.year + 1;
      document.getElementById("year-slider").value = state.year;
      render();
    }, 600);
  }
}

function getValuesForYear(varName, year) {
  const yKey = String(year);
  const out = [];
  for (const [abbr, byYear] of Object.entries(state.panel)) {
    const cell = byYear[yKey];
    if (cell && cell[varName] != null && !Number.isNaN(cell[varName])) {
      out.push({ abbr, value: cell[varName] });
    }
  }
  return out;
}

function getDomainAcrossYears(varName) {
  // Use a fixed cross-year domain so animation doesn't flicker the legend.
  let lo = Infinity, hi = -Infinity;
  for (const byYear of Object.values(state.panel)) {
    for (const cell of Object.values(byYear)) {
      const v = cell[varName];
      if (v == null || Number.isNaN(v)) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
  }
  if (!Number.isFinite(lo)) return [0, 1];
  return [lo, hi];
}

function buildScale(meta, varName) {
  if (meta.scale === "binary") {
    return v => v == 1 ? BINARY_COLORS[1] : BINARY_COLORS[0];
  }
  const [lo, hi] = getDomainAcrossYears(varName);
  const palette = CATEGORY_PALETTE[meta.category] || d3.interpolateBlues;
  const domainLo = meta.unit && meta.unit.startsWith("share") ? Math.min(0, lo) : lo;
  const scale = d3.scaleSequential(palette).domain([domainLo, hi]);
  scale._isBinary = false;
  scale._domain = [domainLo, hi];
  return scale;
}

function render() {
  const meta = state.metadata[state.variable];
  document.getElementById("year-display").textContent = state.year;
  document.getElementById("info-label").textContent = meta.label;
  document.getElementById("info-category").textContent = meta.category;
  document.getElementById("info-unit").textContent = meta.unit;
  const obs = meta.observed_year_range || meta.year_range;
  document.getElementById("info-coverage").textContent = `${obs[0]}–${obs[1]}`;
  document.getElementById("info-definition").textContent = meta.definition;
  const srcSpan = document.getElementById("info-source");
  srcSpan.innerHTML = "";
  const a = document.createElement("a");
  a.href = meta.source_url;
  a.textContent = meta.source;
  a.target = "_blank";
  a.rel = "noopener";
  srcSpan.appendChild(a);
  const caveatEl = document.getElementById("info-caveat");
  if (meta.caveat) {
    caveatEl.textContent = "Caveat: " + meta.caveat;
    caveatEl.hidden = false;
  } else {
    caveatEl.hidden = true;
  }

  const values = getValuesForYear(state.variable, state.year);
  const valueByAbbr = new Map(values.map(d => [d.abbr, d.value]));
  const colorScale = buildScale(meta, state.variable);

  const noteEl = document.getElementById("coverage-note");
  if (values.length === 0) {
    noteEl.textContent = `No data for ${meta.label} in ${state.year}.`;
  } else {
    const missing = 50 - values.length;
    noteEl.textContent = missing > 0
      ? `${values.length}/50 states with data in ${state.year} (${missing} shown as no data).`
      : `Showing all 50 states for ${state.year}.`;
  }

  drawMap(valueByAbbr, colorScale, meta);
  drawLegend(colorScale, meta);
  if (state.hoveredAbbr) showHover(state.hoveredAbbr);
}

let projection, path, mapInitialized = false;

function drawMap(valueByAbbr, colorScale, meta) {
  const svg = d3.select("#map");
  const width = 960, height = 600;
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  if (!mapInitialized) {
    projection = d3.geoAlbersUsa().scale(1280).translate([width/2, height/2 - 20]);
    path = d3.geoPath(projection);
    const states = topojson.feature(state.topology, state.topology.objects.states).features
      .filter(f => FIPS_TO_ABBR[f.id]);

    svg.append("g").attr("class", "states")
      .selectAll("path")
      .data(states, d => d.id)
      .join("path")
        .attr("class", "state")
        .attr("d", path)
        .attr("data-abbr", d => FIPS_TO_ABBR[d.id])
        .on("mousemove", (event, d) => {
          const abbr = FIPS_TO_ABBR[d.id];
          state.hoveredAbbr = abbr;
          showHover(abbr);
          showTooltip(event, abbr);
        })
        .on("mouseleave", hideTooltip);
    mapInitialized = true;
  }

  svg.select(".states").selectAll(".state")
    .each(function(d) {
      const abbr = FIPS_TO_ABBR[d.id];
      const v = valueByAbbr.get(abbr);
      const sel = d3.select(this);
      if (v == null) {
        sel.classed("no-data", true).attr("fill", null);
      } else {
        sel.classed("no-data", false).attr("fill", colorScale(v));
      }
    });
}

function drawLegend(colorScale, meta) {
  const container = d3.select("#legend");
  container.selectAll("*").remove();
  if (meta.scale === "binary") {
    const html = `
      <div style="display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted);">
        <span style="display:inline-block;width:18px;height:14px;background:${BINARY_COLORS[0]};border:1px solid #c8c8c2;"></span> No (0)
        <span style="display:inline-block;width:18px;height:14px;background:${BINARY_COLORS[1]};margin-left:14px;"></span> Yes (1)
        <span style="margin-left:auto;">Year: ${state.year}</span>
      </div>`;
    container.html(html);
    return;
  }
  const [lo, hi] = colorScale._domain || colorScale.domain();
  const w = 320, h = 40, padX = 10;
  const svg = container.append("svg").attr("viewBox", `0 0 ${w} ${h}`).attr("preserveAspectRatio","xMinYMid meet");
  const defs = svg.append("defs");
  const grad = defs.append("linearGradient").attr("id", "legend-grad");
  const N = 16;
  for (let i = 0; i <= N; i++) {
    grad.append("stop")
      .attr("offset", `${(i/N)*100}%`)
      .attr("stop-color", colorScale(lo + (hi-lo)*i/N));
  }
  svg.append("rect").attr("x", padX).attr("y", 4).attr("width", w-2*padX).attr("height", 12).attr("fill", "url(#legend-grad)");
  const ticks = 5;
  const fmt = (meta.unit && meta.unit.startsWith("share")) ? d3.format(".0%") : (Math.abs(hi) >= 100 ? d3.format(",.0f") : d3.format(".2~f"));
  for (let i = 0; i < ticks; i++) {
    const t = i / (ticks - 1);
    const x = padX + (w - 2*padX) * t;
    const v = lo + (hi - lo) * t;
    svg.append("line").attr("x1", x).attr("x2", x).attr("y1", 16).attr("y2", 20).attr("stroke", "#666");
    svg.append("text").attr("x", x).attr("y", 32).attr("text-anchor", "middle").attr("font-size", 10).attr("fill", "#444").text(fmt(v));
  }
  svg.append("text").attr("x", padX).attr("y", h-2).attr("font-size", 10).attr("fill", "#666").text(meta.unit);
  svg.append("text").attr("x", w-padX).attr("y", h-2).attr("text-anchor", "end").attr("font-size", 10).attr("fill", "#666").text(`Year: ${state.year}`);
}

function showHover(abbr) {
  const meta = state.metadata[state.variable];
  const cell = (state.panel[abbr] || {})[String(state.year)] || {};
  const v = cell[state.variable];
  document.getElementById("hover-state").textContent = `${STATE_NAMES[abbr] || abbr} (${state.year})`;
  const tbl = document.getElementById("hover-table");
  tbl.innerHTML = "";
  function row(label, val) {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td"); td1.textContent = label;
    const td2 = document.createElement("td"); td2.textContent = val;
    tr.appendChild(td1); tr.appendChild(td2); tbl.appendChild(tr);
  }
  row(meta.label, formatValue(v, meta));
  // A few quick context vars (always show when available).
  const contextVars = [
    ["lawtotal", "Tufts law count"],
    ["violent_rate", "Violent crime / 100k"],
    ["homicide_rate", "Homicide / 100k"],
    ["firearm_suicide_rate", "Firearm suicide / 100k"],
    ["ownership_rand", "RAND ownership rate"],
    ["ownership_fss", "FS/S proxy"],
    ["population", "Population"],
  ];
  for (const [v2, label] of contextVars) {
    if (v2 === state.variable) continue;
    const m = state.metadata[v2];
    const val = cell[v2];
    if (val == null) continue;
    row(label, formatValue(val, m));
  }
}

function showTooltip(event, abbr) {
  const tt = document.getElementById("tooltip");
  const meta = state.metadata[state.variable];
  const cell = (state.panel[abbr] || {})[String(state.year)] || {};
  const v = cell[state.variable];
  tt.innerHTML = `
    <strong>${STATE_NAMES[abbr] || abbr}</strong>
    <span class="ttvalue">${meta.label}: ${formatValue(v, meta)}</span><br>
    <span class="ttmuted">Year: ${state.year}</span>
  `;
  tt.hidden = false;
  const pad = 12;
  const ttW = tt.offsetWidth, ttH = tt.offsetHeight;
  const docW = document.documentElement.clientWidth;
  let x = event.pageX + pad;
  let y = event.pageY + pad;
  if (x + ttW > docW - 8) x = event.pageX - ttW - pad;
  if (y < window.scrollY + 8) y = window.scrollY + 8;
  tt.style.left = x + "px";
  tt.style.top = y + "px";
}

function hideTooltip() {
  document.getElementById("tooltip").hidden = true;
}

(async function init() {
  try {
    await loadAll();
    populateSelectors();
    render();
  } catch (err) {
    console.error("Failed to load map data:", err);
    const note = document.getElementById("coverage-note");
    note.style.color = "#a4332b";
    note.textContent = "Failed to load data files. If you are previewing locally, serve the docs/ folder over HTTP (file:// won't work). See README.";
  }
})();
