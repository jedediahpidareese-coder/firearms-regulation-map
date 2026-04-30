/* Interactive choropleth: U.S. firearm regulation, ownership, crime, suicides, demographics.
 *
 * Two modes:
 *   "state":  loads data/{manifest,metadata,panel}.json once and renders 50 states.
 *             Topology: us-atlas states-10m.
 *   "county": loads data/county_{manifest,meta}.json once and lazy-loads
 *             data/county/{year}.json on year change. Renders 3,133 counties.
 *             Topology: us-atlas counties-10m.
 *
 * The user toggles between modes via the radio group in the header. The render
 * pipeline is the same in both modes; the differences are encapsulated by the
 * `mode` object the rest of the code reads from.
 */

const TOPO_URLS = {
  state:  "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json",
  county: "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json",
};

// 2-digit FIPS -> postal abbreviation.
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

const CATEGORY_PALETTE = {
  "Regulation":               d3.interpolateBlues,
  "Crime":                    d3.interpolateOrRd,
  "Suicide & firearm deaths": d3.interpolatePuRd,
  "Gun ownership":            d3.interpolateGreens,
  "Demographics":             d3.interpolateViridis,
  "Economy":                  d3.interpolateYlGnBu,
};
const BINARY_COLORS = ["#dadad6", "#1f3a5f"];

// `state` is page state, `mode` is the currently active geography backend.
const state = {
  modeName: "state",
  modes: {},          // populated by buildStateMode / buildCountyMode
  variable: null,
  year: null,
  hoveredKey: null,
  playing: false,
  playTimer: null,
};

const fmtAuto       = d3.format(",.2~f");
const fmtFraction   = d3.format(".1%");
const fmtPercentPre = d3.format(".1f");
const fmtInt        = d3.format(",");

function formatValue(val, meta) {
  if (val == null || Number.isNaN(val)) return "no data";
  switch (meta && meta.format) {
    case "binary":      return val == 1 ? "Yes" : "No";
    case "percent":     return fmtFraction(val);
    case "percent_pre": return fmtPercentPre(val) + "%";
    case "currency":    return "$" + fmtInt(Math.round(val));
    case "integer":     return fmtInt(Math.round(val));
    case "rate":        return Math.abs(val) >= 100 ? fmtInt(Math.round(val)) : fmtAuto(val);
    default:
      return Math.abs(val) >= 100 ? fmtInt(Math.round(val)) : fmtAuto(val);
  }
}
function tickFormatterFor(meta, hi) {
  switch (meta && meta.format) {
    case "percent":     return d3.format(".0%");
    case "percent_pre": return v => d3.format(".0f")(v) + "%";
    case "currency":    return v => "$" + d3.format(",.0f")(v);
    case "integer":     return d3.format(",.0f");
    case "binary":      return v => (v == 1 ? "Yes" : "No");
    default:            return Math.abs(hi) >= 100 ? d3.format(",.0f") : d3.format(".2~f");
  }
}

// ---------- mode constructors ----------

async function buildStateMode() {
  const [manifest, metadata, panel, topology] = await Promise.all([
    d3.json("data/manifest.json"),
    d3.json("data/metadata.json"),
    d3.json("data/panel.json"),
    d3.json(TOPO_URLS.state),
  ]);
  return {
    name: "state",
    manifest, metadata,
    topology,
    topoObjectName: "states",
    hoverHeading: "Selected state",
    keyForFeature: f => FIPS_TO_ABBR[f.id] || null,
    keyToDisplayName: k => STATE_NAMES[k] || k,
    valueByKey(varName, year) {
      const yKey = String(year);
      const out = new Map();
      for (const [abbr, byYear] of Object.entries(panel)) {
        const cell = byYear[yKey];
        if (cell && cell[varName] != null && !Number.isNaN(cell[varName])) {
          out.set(abbr, cell[varName]);
        }
      }
      return out;
    },
    contextRow(varName, key) {
      const cell = (panel[key] || {})[String(state.year)] || {};
      return cell;
    },
    domain(varName) {
      let lo = Infinity, hi = -Infinity;
      for (const byYear of Object.values(panel)) {
        for (const cell of Object.values(byYear)) {
          const v = cell[varName];
          if (v == null || Number.isNaN(v)) continue;
          if (v < lo) lo = v;
          if (v > hi) hi = v;
        }
      }
      return Number.isFinite(lo) ? [lo, hi] : [0, 1];
    },
    countLabel(values) {
      const n = values.size;
      const missing = 50 - n;
      if (n === 0) return null;
      return missing > 0
        ? `${n}/50 states with data in ${state.year} (${missing} shown as no data).`
        : `Showing all 50 states for ${state.year}.`;
    },
    contextVars: [
      ["lawtotal", "Tufts law count"],
      ["violent_rate", "Violent crime / 100k"],
      ["homicide_rate", "Homicide / 100k"],
      ["firearm_suicide_rate", "Firearm suicide / 100k"],
      ["ownership_rand", "RAND ownership rate"],
      ["ownership_fss", "FS/S proxy"],
      ["population", "Population"],
    ],
  };
}

async function buildCountyMode() {
  const [manifest, metadata, topology] = await Promise.all([
    d3.json("data/county_manifest.json"),
    d3.json("data/county_meta.json"),
    d3.json(TOPO_URLS.county),
  ]);
  const yearCache = new Map();
  // Pre-load default year so the first render has data.
  const defYear = manifest.default_year;
  yearCache.set(defYear, await d3.json(`data/county/${defYear}.json`));

  // Helper that fires a load if the requested year isn't in cache yet.
  // Render reads from cache; if missing, it triggers a load and re-renders
  // when the load settles.
  function ensureYearLoaded(year) {
    if (yearCache.has(year)) return Promise.resolve(yearCache.get(year));
    const url = `data/county/${year}.json`;
    return d3.json(url).then(d => { yearCache.set(year, d); return d; });
  }

  // Quick cross-year domain estimator: only uses years already in cache.
  // For unloaded years we rely on the loaded ones; the legend will tighten
  // as more years are loaded by year-slider scrubbing.
  function quickDomain(varName) {
    let lo = Infinity, hi = -Infinity;
    for (const byCounty of yearCache.values()) {
      for (const cell of Object.values(byCounty)) {
        const v = cell[varName];
        if (v == null || Number.isNaN(v)) continue;
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    return Number.isFinite(lo) ? [lo, hi] : [0, 1];
  }

  return {
    name: "county",
    manifest, metadata,
    topology,
    topoObjectName: "counties",
    hoverHeading: "Selected county",
    keyForFeature: f => String(f.id).padStart(5, "0"),
    keyToDisplayName: k => {
      // The county FIPS is the key, but the display name lives in our cache.
      const cur = yearCache.get(state.year) || {};
      const cell = cur[k];
      // We didn't ship name in the per-year files (size). Show FIPS.
      return k;
    },
    valueByKey(varName, year) {
      const byCounty = yearCache.get(year);
      const out = new Map();
      if (!byCounty) {
        // Trigger a background load and a follow-up render.
        ensureYearLoaded(year).then(() => render());
        return out;
      }
      for (const [fips, cell] of Object.entries(byCounty)) {
        const v = cell[varName];
        if (v != null && !Number.isNaN(v)) out.set(fips, v);
      }
      return out;
    },
    contextRow(varName, key) {
      const cur = yearCache.get(state.year) || {};
      return cur[key] || {};
    },
    domain: quickDomain,
    countLabel(values) {
      const n = values.size;
      if (n === 0) return null;
      const missing = 3133 - n;
      return missing > 0
        ? `${n.toLocaleString()}/3,133 counties with data in ${state.year} (${missing} shown as no data).`
        : `Showing all 3,133 counties for ${state.year}.`;
    },
    contextVars: [
      ["county_violent_crime_rate", "Violent crime / 100k"],
      ["county_property_crime_rate", "Property crime / 100k"],
      ["county_murder_rate", "Murder / 100k"],
      ["state_firearm_suicide_rate", "State firearm suicide / 100k"],
      ["share_white_nh", "Share NH white"],
      ["share_black_nh", "Share NH Black"],
      ["share_hispanic", "Share Hispanic"],
      ["share_bachelors_plus", "Share bachelor's+"],
      ["unemployment_rate", "Unemployment %"],
      ["pcpi_real_2024", "Per-capita income ($2024)"],
      ["population", "Population"],
      ["lawtotal", "State firearm law count"],
    ],
    ensureYearLoaded,
  };
}

// ---------- mode-agnostic UI ----------

function currentMode() { return state.modes[state.modeName]; }

function populateSelectors(mode) {
  // 1) Initialize the year slider FIRST so state.year is set before any render.
  const slider = document.getElementById("year-slider");
  const [yMin, yMax] = mode.manifest.year_range;
  slider.min = yMin; slider.max = yMax;
  if (state.year == null || state.year < yMin || state.year > yMax) {
    slider.value = mode.manifest.default_year;
  } else {
    slider.value = state.year;
  }
  state.year = +slider.value;
  document.getElementById("year-min").textContent = yMin;
  document.getElementById("year-max").textContent = yMax;

  // 2) Build the category + variable selectors. To avoid stacking listeners
  //    across mode switches, replace the existing nodes with fresh clones first
  //    and look them up again afterwards.
  const oldCat = document.getElementById("category-select");
  const oldVar = document.getElementById("variable-select");
  oldCat.parentNode.replaceChild(oldCat.cloneNode(false), oldCat);
  oldVar.parentNode.replaceChild(oldVar.cloneNode(false), oldVar);
  const catSel = document.getElementById("category-select");
  const varSel = document.getElementById("variable-select");

  const cats = Object.keys(mode.manifest.categories).sort();
  cats.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c; opt.textContent = c;
    catSel.appendChild(opt);
  });
  const defaultVar = mode.manifest.default_variable;
  const defaultMeta = mode.metadata[defaultVar];
  catSel.value = defaultMeta.category;

  function refreshVarSelect() {
    varSel.innerHTML = "";
    const vars = mode.manifest.categories[catSel.value];
    vars.forEach(v => {
      const meta = mode.metadata[v];
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

  state.variable = defaultVar;
  refreshVarSelect();
  varSel.value = state.variable;
}

function clampYearToVariable() {
  const mode = currentMode();
  const meta = mode.metadata[state.variable];
  if (!meta || !meta.observed_year_range) return;
  if (state.year == null) return; // slider not initialized yet
  const [vMin, vMax] = meta.observed_year_range;
  const slider = document.getElementById("year-slider");
  if (state.year < vMin) state.year = vMin;
  if (state.year > vMax) state.year = vMax;
  slider.value = state.year;
}

function togglePlay() {
  const btn = document.getElementById("play-button");
  const mode = currentMode();
  if (state.playing) {
    clearInterval(state.playTimer);
    state.playing = false;
    btn.classList.remove("playing");
    btn.innerHTML = "&#9654;";
  } else {
    state.playing = true;
    btn.classList.add("playing");
    btn.innerHTML = "&#9632;";
    const meta = mode.metadata[state.variable];
    const [vMin, vMax] = meta.observed_year_range || mode.manifest.year_range;
    state.playTimer = setInterval(() => {
      state.year = state.year >= vMax ? vMin : state.year + 1;
      document.getElementById("year-slider").value = state.year;
      render();
    }, 700);
  }
}

function buildScale(meta, mode) {
  if (meta.format === "binary" || meta.scale === "binary") {
    return v => v == 1 ? BINARY_COLORS[1] : BINARY_COLORS[0];
  }
  const [lo, hi] = mode.domain(state.variable);
  const palette = CATEGORY_PALETTE[meta.category] || d3.interpolateBlues;
  const domainLo = (meta.format === "percent" || meta.format === "percent_pre")
    ? Math.min(0, lo) : lo;
  const scale = d3.scaleSequential(palette).domain([domainLo, hi]);
  scale._domain = [domainLo, hi];
  return scale;
}

let projection, path, mapDrawnFor = null;

function ensureMapDrawn(mode) {
  // Tear down and re-create the SVG only when the active mode changes
  // (state vs county have different topology and feature counts).
  if (mapDrawnFor === mode.name) return;
  mapDrawnFor = mode.name;
  const svg = d3.select("#map");
  svg.selectAll("*").remove();
  const width = 960, height = 600;
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  projection = d3.geoAlbersUsa().scale(1280).translate([width / 2, height / 2 - 20]);
  path = d3.geoPath(projection);

  const featCol = topojson.feature(mode.topology, mode.topology.objects[mode.topoObjectName]);
  const features = featCol.features.filter(f => mode.keyForFeature(f) != null);

  // Render in a single batch. For 3,133 counties this is ~3 MB of SVG; D3
  // handles it but we omit per-element transitions to keep it snappy.
  svg.append("g").attr("class", "regions")
    .selectAll("path")
    .data(features, d => d.id)
    .join("path")
      .attr("class", mode.name === "state" ? "state" : "county")
      .attr("d", path)
      .attr("data-key", d => mode.keyForFeature(d))
      .on("mousemove", (event, d) => {
        const k = mode.keyForFeature(d);
        state.hoveredKey = k;
        showHover(k);
        showTooltip(event, k);
      })
      .on("mouseleave", hideTooltip);

  // For county mode, also overlay state borders so the map is readable.
  if (mode.name === "county" && mode.topology.objects.states) {
    const stateBorders = topojson.mesh(
      mode.topology, mode.topology.objects.states, (a, b) => a !== b
    );
    svg.append("path")
      .attr("class", "state-border")
      .attr("fill", "none")
      .attr("stroke", "rgba(0,0,0,0.55)")
      .attr("stroke-width", 0.7)
      .attr("d", path(stateBorders));
  }
}

function render() {
  const mode = currentMode();
  const meta = mode.metadata[state.variable];

  document.getElementById("year-display").textContent = state.year;
  document.getElementById("info-label").textContent = meta.label;
  document.getElementById("info-category").textContent = meta.category;
  document.getElementById("info-unit").textContent = meta.unit;
  const obs = meta.observed_year_range || meta.year_range || mode.manifest.year_range;
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
  document.getElementById("hover-heading").textContent = mode.hoverHeading;

  ensureMapDrawn(mode);
  const valueByKey = mode.valueByKey(state.variable, state.year);
  const colorScale = buildScale(meta, mode);

  const noteEl = document.getElementById("coverage-note");
  noteEl.textContent = mode.countLabel(valueByKey)
    || `No data for ${meta.label} in ${state.year}.`;

  d3.select("#map").select(".regions").selectAll("path")
    .each(function(d) {
      const k = mode.keyForFeature(d);
      const v = valueByKey.get(k);
      const sel = d3.select(this);
      if (v == null) {
        sel.classed("no-data", true).attr("fill", null);
      } else {
        sel.classed("no-data", false).attr("fill", colorScale(v));
      }
    });

  drawLegend(colorScale, meta);
  if (state.hoveredKey) showHover(state.hoveredKey);
}

function drawLegend(colorScale, meta) {
  const container = d3.select("#legend");
  container.selectAll("*").remove();
  if (meta.format === "binary" || meta.scale === "binary") {
    container.html(`
      <div class="legend-binary">
        <span class="swatch" style="background:${BINARY_COLORS[0]};border:1px solid #c8c8c2;"></span> No
        <span class="swatch" style="background:${BINARY_COLORS[1]};margin-left:14px;"></span> Yes
      </div>
      <div class="legend-caption">
        <span>${meta.unit}</span><span>Year: ${state.year}</span>
      </div>
    `);
    return;
  }
  const [lo, hi] = colorScale._domain || colorScale.domain();
  const w = 320, h = 34, padX = 10;
  const svg = container.append("svg")
      .attr("viewBox", `0 0 ${w} ${h}`)
      .attr("preserveAspectRatio", "xMinYMid meet");
  const grad = svg.append("defs").append("linearGradient").attr("id", "legend-grad");
  const N = 16;
  for (let i = 0; i <= N; i++) {
    grad.append("stop")
      .attr("offset", `${(i / N) * 100}%`)
      .attr("stop-color", colorScale(lo + (hi - lo) * i / N));
  }
  svg.append("rect").attr("x", padX).attr("y", 4)
     .attr("width", w - 2 * padX).attr("height", 12).attr("fill", "url(#legend-grad)");
  const ticks = 5;
  const fmt = tickFormatterFor(meta, hi);
  for (let i = 0; i < ticks; i++) {
    const t = i / (ticks - 1);
    const x = padX + (w - 2 * padX) * t;
    const v = lo + (hi - lo) * t;
    svg.append("line").attr("x1", x).attr("x2", x).attr("y1", 16).attr("y2", 20)
       .attr("stroke", "#666");
    svg.append("text")
        .attr("x", x).attr("y", 30)
        .attr("text-anchor", i === 0 ? "start" : (i === ticks - 1 ? "end" : "middle"))
        .attr("font-size", 10).attr("fill", "#444")
        .text(fmt(v));
  }
  container.append("div")
      .attr("class", "legend-caption")
      .html(`<span>${meta.unit}</span><span>Year: ${state.year}</span>`);
}

function showHover(key) {
  const mode = currentMode();
  const meta = mode.metadata[state.variable];
  const cell = mode.contextRow(state.variable, key);
  const v = cell[state.variable];
  document.getElementById("hover-state").textContent =
    `${mode.keyToDisplayName(key)} (${state.year})`;
  const tbl = document.getElementById("hover-table");
  tbl.innerHTML = "";
  function row(label, val) {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td"); td1.textContent = label;
    const td2 = document.createElement("td"); td2.textContent = val;
    tr.appendChild(td1); tr.appendChild(td2); tbl.appendChild(tr);
  }
  row(meta.label, formatValue(v, meta));
  for (const [v2, label] of mode.contextVars) {
    if (v2 === state.variable) continue;
    const m = mode.metadata[v2];
    if (!m) continue;
    const val = cell[v2];
    if (val == null) continue;
    row(label, formatValue(val, m));
  }
}

function showTooltip(event, key) {
  const mode = currentMode();
  const tt = document.getElementById("tooltip");
  const meta = mode.metadata[state.variable];
  const cell = mode.contextRow(state.variable, key);
  const v = cell[state.variable];
  tt.innerHTML = `
    <strong>${mode.keyToDisplayName(key)}</strong>
    <span class="ttvalue">${meta.label}: ${formatValue(v, meta)}</span><br>
    <span class="ttmuted">Year: ${state.year}</span>
  `;
  tt.hidden = false;
  const pad = 12;
  const ttW = tt.offsetWidth;
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
  state.hoveredKey = null;
}

// ---------- mode switching + bootstrap ----------

async function switchToMode(name) {
  state.modeName = name;
  if (!state.modes[name]) {
    document.getElementById("coverage-note").textContent = "Loading " + name + " data ...";
    state.modes[name] = name === "state" ? await buildStateMode() : await buildCountyMode();
  }
  populateSelectors(state.modes[name]);
  render();
}

(async function init() {
  try {
    document.getElementById("coverage-note").textContent = "Loading state data ...";
    state.modes.state = await buildStateMode();
    populateSelectors(state.modes.state);

    // Year slider listener (single registration, reads currentMode every input).
    const slider = document.getElementById("year-slider");
    slider.addEventListener("input", () => {
      state.year = +slider.value;
      render();
    });
    document.getElementById("play-button").addEventListener("click", togglePlay);

    // Geography toggle.
    document.querySelectorAll('input[name="geo-mode"]').forEach(r => {
      r.addEventListener("change", e => switchToMode(e.target.value));
    });

    // Generated timestamp.
    const ga = state.modes.state.manifest.generated_at;
    document.getElementById("generated-at").textContent =
      ga.replace("T", " ").replace("Z", " UTC");

    render();
  } catch (err) {
    console.error("Failed to load map data:", err);
    const note = document.getElementById("coverage-note");
    note.style.color = "#a4332b";
    note.textContent = "Failed to load data files. Open the page over HTTP, not file://. " +
      "Run: python -m http.server 8765 -d docs";
  }
})();
