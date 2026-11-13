# Offline Font Awesome outlines

`fontawesome.json` contains the Free solid (`fas`), regular (`far`), and brands (`fab`) SVG outlines and their historical name aliases. The Node adapter resolves an icon to `path` and `viewBox` before calling the existing WASM writer; it remains a native editable vector, not an ellipse placeholder or a downloaded image.

The catalog is generated from the exact Font Awesome package versions pinned at the repository root by `tools/pptd/build_icons.mjs`. npm packages are build dependencies only. No browser or network request is made to resolve an icon at runtime.

Font Awesome Free SVG icons are licensed under CC BY 4.0; the upstream license file is bundled as `LICENSE` and includes the project's other component licenses. Source: https://fontawesome.com/license/free and https://github.com/FortAwesome/Font-Awesome. Brand marks retain their owners' trademarks.
