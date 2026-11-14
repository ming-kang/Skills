# Vendored runtime JavaScript

These ESM files run without adjacent npm packages or a browser. Development sources and build tooling live in `tools/pptd/build_vendor.mjs` at the repository, not in the distributed skill.

| Bundle | Runtime scope |
|---|---|
| ECharts 6.1.0 | Heatmap, treemap, sunburst, sankey; SVG renderer, grid, title and continuous colorbar only |
| fontkit 2.0.4 | TrueType/OpenType SFNT and TTC glyph parsing/layout; EOT is unwrapped by the adapter. No WOFF/WOFF2/DFont or Brotli |
| KaTeX 0.18.2 | Strict LaTeX → MathML for editable Office Math |
| xmldom 0.9.12 | XML/HTML/SVG DOM parsing and serialization |
| YAML 2.9.1 | YAML 1.2 core-schema parsing |

Each bundle has its upstream licenses/notices under `licenses/<name>/`. fontkit's
source bundle retains its complete shaping engine and Unicode tries; its legacy
cache decorators and static trie assets are resolved at build time. See its
`licenses/fontkit/NOTICE` for actual package inputs and restored authoritative
license sources. Selected font files retain separate licenses.

No extra WASM or runtime installer is involved. The presentation writer lives
separately under `../wasm/` and is version-locked to its Node adapter.
