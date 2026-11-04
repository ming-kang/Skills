# Advanced chart SVG renderer

`echarts.mjs` is the unmodified, standalone `dist/echarts.esm.min.mjs` from Apache ECharts **6.0.0**. It includes zrender **6.0.0** and tslib **2.3.0**. The local exporter loads it only for heatmap, treemap, sunburst, and sankey charts, using SVG server-side rendering without a browser, canvas, network access, or runtime npm packages.

The exporter embeds these charts as `.svg` pictures with their original definitions in SVG metadata. They are not native PowerPoint chart objects and have no PNG fallback.

Repository maintainers refresh the asset with `npm run pptd:build-charts`; the copy script and development dependency live outside the distributed skill.

Upstream notices distributed with this asset:

- `LICENSE`, `NOTICE`: Apache ECharts (Apache-2.0).
- `licenses/LICENSE-d3`: embedded d3 subcomponents (BSD-3-Clause).
- `licenses/LICENSE-zrender`: zrender (BSD-3-Clause).
- `licenses/LICENSE-tslib`, `licenses/CopyrightNotice-tslib.txt`: tslib (0BSD).
