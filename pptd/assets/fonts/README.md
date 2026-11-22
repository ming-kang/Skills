# Licensed offline font assets

`catalog.json` records 22 original static TrueType faces and their exact source
URLs. Files are stored as lossless `.ttf.gz` to reduce the installed skill's
size; only selected fonts are decoded and used. This is not a web subset or a
modified font.

The Latin set (Inter, Liter, Hedvig Letters Sans, Oranienbaum, Quattrocento Sans, Sorts
Mill Goudy, Unna, Coda, Jersey 15 and Jersey 20 Charted) and Noto Sans SC remain
complete. Non-RIBBI faces keep their Windows family identity: Coda ExtraBold is
not falsely registered as Coda Bold. Each family directory retains its original
OFL license and copyright.

`tools/pptd/build_fonts.mjs` rebuilds storage from the catalog's pinned sources.
Intact installed payloads make normal rebuilds offline; missing or corrupt files
are restored from the recorded sources. Build tooling remains outside the
distributed skill.

The runtime converts eligible TTF/TTC faces to uncompressed EOT for the writer.
Embedding and SVG labels share the same selected original bytes. It does not
install fonts, use a browser, depend on fontTools, or ship loose Windows fonts.
Respect fsType and original family/style bindings; embedding is not proof of
identical visual playback.

MiSans and uncleared commercial/custom families are not redistributed. Use an
installed or properly licensed project-local copy for exact typography. Missing
families, unavailable styles and non-embeddable faces are reported; substitutions
are not represented as exact brand-font matches.
