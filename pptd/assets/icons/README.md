# Offline Font Awesome outlines

`fontawesome.json` contains the Free solid (`fas`), regular (`far`), and brands (`fab`) SVG outlines and their historical name aliases. The Node adapter resolves an icon to `path` and `viewBox` before calling the existing WASM writer; it remains a native editable vector, not an ellipse placeholder or a downloaded image.

The generated catalog is pre-vendored runtime data, including historical aliases; `pptd:build-assets` does not rebuild it. No npm packages, browser or network request are needed to resolve an icon at runtime.

Font Awesome Free SVG icons are licensed under CC BY 4.0; the upstream license file is bundled as `LICENSE` and includes the project's other component licenses. Source: https://fontawesome.com/license/free and https://github.com/FortAwesome/Font-Awesome. Brand marks retain their owners' trademarks.
