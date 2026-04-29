# Interactive map of U.S. firearm regulation, ownership, and outcomes

This `docs/` directory is the source for a static GitHub Pages site that lets visitors explore a balanced state-year panel of U.S. firearm regulation, gun ownership proxies, crime, suicide and firearm-related deaths, and demographics from 1979 onward.

- [`index.html`](index.html) &mdash; the interactive choropleth (year slider + variable selector)
- [`about.html`](about.html) &mdash; definitions, sources, manipulations, and reproduction instructions
- [`data/`](data/) &mdash; the JSON files the page consumes (`panel.json`, `metadata.json`, `manifest.json`)
- [`js/app.js`](js/app.js) &mdash; D3 + TopoJSON map logic
- [`css/style.css`](css/style.css) &mdash; styling

## Rebuild the data

```sh
python ../scripts/build_website_data.py
```

That script reads the balanced panels in `../data/processed/` (built upstream by `../scripts/build_firearms_panel.py`), the firearm-suicide/homicide v2 dataset, OpenCrime granular crime trends, and RAND TL-354 household firearm ownership, then emits the three JSON files this page needs.

## Preview locally

The data files are loaded via `fetch()`, so opening `index.html` directly with `file://` will not work. Serve the directory:

```sh
python -m http.server 8765 -d docs
```

then open <http://localhost:8765/>.
