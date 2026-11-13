# Licensed offline font assets

`catalog.json` lists original static TrueType faces, exact source URLs and SHA-256 values. The Latin recommendation set (Liter, Hedvig Letters Sans, Oranienbaum, Quattrocento Sans, Sorts Mill Goudy, Unna, Coda, Jersey 15 and Jersey 20 Charted) and a Noto Sans SC fallback are included. Non-RIBBI faces retain their own Windows family identity, for example Coda ExtraBold is not falsely registered as Coda Bold.

Every family directory includes its upstream OFL license/copyright. Sources are pinned in `tools/pptd/build_fonts.py`; the CJK file is a complete static Google Fonts TrueType resource, not a text-specific web subset. Build tooling stays outside the distributed skill.

The runtime resolves effective used fonts and converts eligible TTF/TTC faces to uncompressed EOT for the private writer. It does not install fonts, ship loose Windows fonts, use a browser, or depend on fontTools. Document embedding permissions (`fsType`) and original style-linked family/subfamily names are respected. Font embedding and visual playback remain separate verification steps.

MiSans and other uncleared commercial/custom families are not redistributed here. Use an installed or properly licensed project-local copy when exact typography is required. Missing families and non-embeddable faces are explicitly reported; the fallback is not represented as an exact brand-font match.
