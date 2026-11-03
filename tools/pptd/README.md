# pptd — repository development notes

The distributable skill is the repository-root `pptd/` folder. This directory contains only development tests and fixtures.

## Runtime map

```text
pptd/
  SKILL.md
  assets/wasm/pptd_wasm_bg.wasm  # sole private writer binary
  references/                    # format + all design guides and 44 presets
  scripts/
    validate_pptd.py             # public structural-validation CLI
    export_pptx.py               # public validation + export CLI
    pptd_deck.py                 # YAML loading, project paths, structural checks
    pptd_pptx.py                 # transition patching + PPTX verification
    pptd_common.py               # shared error, path, logging, process helpers
    export_pptd.mjs              # JSON handoff, media resolution, WASM invocation
    wasm-exporter.mjs            # version-locked wasm-bindgen adapter
```

The Python wrapper owns YAML parsing and slide-transition policy. It passes pre-parsed JSON to Node, so the installed skill needs no adjacent `node_modules`. The Node side resolves media and invokes the private writer. Browser editing, image export, browser automation, and process-reaping code are intentionally outside the core skill.

## Tests

```text
tools/pptd/
  tests/
    test_export_pptx.py
    fixtures/minimal/            # one text slide
    fixtures/qa-deck/            # three slides + local media
  tests-node/
    exporter.test.js             # project/media normalization without a browser
```

Run:

```bash
npm run test:pptd
node --test "tools/pptd/tests-node/*.test.js"
python -B -m unittest discover -s tools/pptd/tests -p "test_*.py"
```

The Python suite includes real Node + WASM exports and skips those cases only when Node is unavailable. No test needs a browser or network access.

## Invariants

- **Byte-stable WASM.** The canonical binary is `pptd/assets/wasm/pptd_wasm_bg.wasm`, SHA-256 `589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e`. Keep exactly one `.wasm` in the distributed skill. The adapter expects this build's imports and exports; a replacement requires real export testing.
- **Format compatibility.** `references/pptd.md` is the authoritative private v2 contract. Do not invent fields or weaken project-path containment to accommodate a deck.
- **No browser fallback.** Deck, dependency, and export errors are reported directly. The runtime does not auto-install packages or start background processes.
- **Single transition owner.** `export_pptx.py` patches and verifies root-level slide transitions after WASM export. `p:transition` must follow `cSld`/optional `clrMapOvr` and precede `timing`/`extLst`.
- **Honest verification.** ZIP/XML checks do not establish rendering fidelity or application compatibility. The core does not claim font embedding or rendered visual QA.
- **Design reference coverage.** Keep all seven scenario guides and all 44 presets. `references/design_system/README.md` maps each theme ID to `<theme-id>.md` beside the index; update it whenever a preset is added, removed, or renamed.
- **Clean distribution.** Runtime helpers and assets stay inside `pptd/`; repository-only tests stay here. Remove `__pycache__` and generated exports before packaging.
