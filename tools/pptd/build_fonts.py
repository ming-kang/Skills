#!/usr/bin/env python3
"""Vendor licensed original fonts, not the former editor's undocumented EOT files."""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pptd" / "scripts"))
from font_data import read_font_faces  # noqa: E402

REF = "86aced91de05cd4f96a06838124cca45be337b2b"
BASE = f"https://raw.githubusercontent.com/google/fonts/{REF}/ofl/"
OUTPUT = ROOT / "pptd" / "assets" / "fonts"
FAMILIES = [
    ("Liter", "liter", "Liter", ["Regular"], []),
    ("Hedvig Letters Sans", "hedvigletterssans", "HedvigLettersSans", ["Regular"], ["HedvigLettersSans"]),
    ("Oranienbaum", "oranienbaum", "Oranienbaum", ["Regular"], []),
    ("Quattrocento Sans", "quattrocentosans", "QuattrocentoSans", ["Regular", "Bold", "Italic", "BoldItalic"], ["QuattrocentoSans"]),
    ("Sorts Mill Goudy", "sortsmillgoudy", "SortsMillGoudy", ["Regular", "Italic"], ["SortsMillGoudy"]),
    ("Unna", "unna", "Unna", ["Regular", "Bold", "Italic", "BoldItalic"], []),
    ("Coda", "coda", "Coda", ["Regular", "ExtraBold"], []),
    ("Jersey 15", "jersey15", "Jersey15", ["Regular"], ["Jersey15"]),
    ("Jersey 20 Charted", "jersey20charted", "Jersey20Charted", ["Regular"], ["Jersey20Charted"]),
]
NOTO = "https://fonts.gstatic.com/s/notosanssc/v41/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_FnYw.ttf"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "pptd-font-build/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError(f"font source exceeds build limit: {url}")
    return data


def main() -> None:
    jobs = []
    aliases = {}
    for family, folder, stem, styles, names in FAMILIES:
        for name in names:
            aliases[name] = family
        jobs.append((family, folder, "OFL.txt", BASE + folder + "/OFL.txt"))
        jobs.extend((family, folder, f"{stem}-{style}.ttf", BASE + folder + "/" + urllib.parse.quote(f"{stem}-{style}.ttf")) for style in styles)
    jobs += [("Noto Sans SC", "notosanssc", "OFL.txt", BASE + "notosanssc/OFL.txt"), ("Noto Sans SC", "notosanssc", "NotoSansSC-Regular.ttf", NOTO)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        payloads = list(pool.map(lambda job: download(job[3]), jobs))
    catalog = {"sourceRevision": REF, "aliases": aliases, "fallbacks": {"latin": "Liter", "ea": "Noto Sans SC"}, "faces": []}
    for (family, folder, filename, source), data in zip(jobs, payloads):
        target = OUTPUT / folder / filename
        if filename.endswith(".ttf"):
            face = read_font_faces(data)[0]
            if face["variable"]:
                raise ValueError(f"expected a static font, got variable source: {source}")
            catalog["faces"].append({"family": face["family"], "slot": face["slot"], "src": f"{folder}/{filename}", "license": f"{folder}/OFL.txt", "source": source, "sha256": hashlib.sha256(data).hexdigest()})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (OUTPUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Vendored {len(catalog['faces'])} static font faces with OFL licenses")


if __name__ == "__main__":
    main()
