# Design System Presets — Index

The pptd skill ships 44 design-system presets. Use them **only when the user explicitly names a theme** — self-directed design must not auto-pick a preset (see `SKILL.md` §step3).

## Rules

- Resolve the theme by the slug the user gave you; paths below are relative to this directory (`references/design_system/`).
- If a slug matches a primary-catalog folder, the folder's `design.md` is the **sole style source** — never mix in another preset.
- Extra-catalog themes have no folder; read the numbered sheet directly.
- If the user names a theme that does not exist here, tell the user; do not substitute a similar-looking preset.

## Primary catalog (30)

| Category | Theme ID | Look | File |
|---|---|---|---|
| Consulting / Strategy | `apricot-white-brief` | Apricot-white consulting brief; dense argumentation, fine-line charts | `consulting/apricot-white-brief/design.md` |
| Consulting / Strategy | `indigo-due-diligence` | Indigo due-diligence look; McKinsey-like density and frameworks | `consulting/indigo-due-diligence/design.md` |
| Consulting / Strategy | `marine-blue-research` | Marine-blue research report layout for professional consulting | `consulting/marine-blue-research/design.md` |
| Consulting / Strategy | `moss-green-transformation` | Moss-green transformation narrative for strategic change | `consulting/moss-green-transformation/design.md` |
| Consulting / Strategy | `pine-green-strategy` | Pine-green strategy; dark title banner + mint accents | `consulting/pine-green-strategy/design.md` |
| Consulting / Strategy | `red-black-growth` | Red-black growth story; high-contrast, conclusion-led | `consulting/red-black-growth/design.md` |
| Finance / Business | `black-gold-ledger` | Black-gold ledger; institutional investment research | `finance/black-gold-ledger/design.md` |
| Finance / Business | `ebony-ledger` | Ebony ledger; dark financial-research tone | `finance/ebony-ledger/design.md` |
| Finance / Business | `honey-orange-memo` | Honey-orange memo; warm business research notes | `finance/honey-orange-memo/design.md` |
| Finance / Business | `lake-blue-memo` | Lake-blue memo; clean financial research notes | `finance/lake-blue-memo/design.md` |
| Finance / Business | `prospect-annual` | Prospect annual; institutional yearbook / research publishing feel | `finance/prospect-annual/design.md` |
| Finance / Business | `rice-paper-annual` | Rice-paper annual; warm off-white paper, bold editorial headlines | `finance/rice-paper-annual/design.md` |
| Work Report | `blue-flame-brand` | Blue-flame brand; conclusion-first business review | `work/blue-flame-brand/design.md` |
| Work Report | `electric-violet-business` | Electric-violet business; operating review and progress updates | `work/electric-violet-business/design.md` |
| Work Report | `moon-white-imagery` | Moon-white imagery; photo-led narrative + business conclusions | `work/moon-white-imagery/design.md` |
| Work Report | `sky-blue-wayfinding` | Sky-blue wayfinding; clear navigational work reports | `work/sky-blue-wayfinding/design.md` |
| Work Report | `warm-clay-works` | Warm-clay works; portfolio-grade polished reviews | `work/warm-clay-works/design.md` |
| Work Report | `warm-jade-annual-report` | Warm-jade annual report; operating yearbook and retros | `work/warm-jade-annual-report/design.md` |
| Promotion / Brand | `aqua-charity-report` | Aqua charity report; brand nonprofit storytelling | `promotion/aqua-charity-report/design.md` |
| Promotion / Brand | `cream-collage` | Cream collage; emotional brand collage narrative | `promotion/cream-collage/design.md` |
| Promotion / Brand | `pine-soot-pictorial` | Pine-soot pictorial; pictorial brand annual | `promotion/pine-soot-pictorial/design.md` |
| Promotion / Brand | `silk-yellow-magazine` | Silk-yellow magazine; dense editorial magazine layout | `promotion/silk-yellow-magazine/design.md` |
| Promotion / Brand | `silver-gray-luxury-magazine` | Silver-gray luxury magazine; premium brand periodical feel | `promotion/silver-gray-luxury-magazine/design.md` |
| Promotion / Brand | `travel-green-handbook` | Travel-green handbook; travel / destination guidebook tone | `promotion/travel-green-handbook/design.md` |
| Academic | `blue-line-courseware` | Blue-line courseware; rigorous academic lecture layout | `academic/blue-line-courseware/design.md` |
| Academic | `deep-blue-atlas` | Deep-blue atlas; research talk and atlas narrative | `academic/deep-blue-atlas/design.md` |
| Academic | `paper-white-courseware` | Paper-white courseware; thesis-defense-level typesetting | `academic/paper-white-courseware/design.md` |
| Academic | `pastel-derivation` | Pastel derivation; formula / step-by-step reveal | `academic/pastel-derivation/design.md` |
| Academic | `teal-green-academic-defense` | Teal-green academic defense; formal thesis defense look | `academic/teal-green-academic-defense/design.md` |
| Academic | `wine-red-data` | Wine-red data; academic data visualization | `academic/wine-red-data/design.md` |

## Extra catalog (14)

Companion sheets that extend the primary catalog; invoke by theme ID the same way.

| Theme ID | Look | File |
|---|---|---|
| `dusk-violet-consulting` | Dusk-violet consulting thought-leadership report | `extra/dusk-violet-consulting.md` |
| `red-black-business` | Red-black management-consulting full-package template | `extra/red-black-business.md` |
| `map-strategy` | Map strategy; internationalization / regional footprint | `extra/map-strategy.md` |
| `xuan-paper-annual` | Xuan-paper annual; ultra-heavy headlines, editorial research journal | `extra/xuan-paper-annual.md` |
| `lead-gray-quarterly` | Lead-gray quarterly; financial-newspaper data monitor | `extra/lead-gray-quarterly.md` |
| `ink-green-market-trends` | Ink-green market trends; dark crypto / market quarterly | `extra/ink-green-market-trends.md` |
| `orange-tech` | Orange tech annual report and business-insight deck | `extra/orange-tech.md` |
| `mist-blue-travelogue` | Mist-blue travelogue; travel / hospitality industry research | `extra/mist-blue-travelogue.md` |
| `color-stripes-documentary` | Color-stripes documentary; impact / ESG long-form narrative | `extra/color-stripes-documentary.md` |
| `red-white-business` | Red-white business; employer brand and org capability | `extra/red-white-business.md` |
| `gold-orange-type-journal` | Gold-orange type-trends journal | `extra/gold-orange-type-journal.md` |
| `fresh-brand` | Fresh brand equity / impact report | `extra/fresh-brand.md` |
| `pink-purple-diagnosis` | Pink-purple cloud-layer diagnostic narrative | `extra/pink-purple-diagnosis.md` |
| `dark-themed-data` | Dark-themed data dashboard for crypto / market research | `extra/dark-themed-data.md` |
