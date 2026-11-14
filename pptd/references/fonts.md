# Font system

The Latin recommendation set and Noto Sans SC are bundled as complete licensed original TrueType fonts (see `assets/fonts/catalog.json`), stored losslessly as `.ttf.gz` and decoded only when selected. Other families below require an installed or authorized project-local font. The CLI resolves effective used families, handles local TTF/TTC/EOT and Google Fonts CSS, and embeds eligible static TrueType faces with correct style bindings. Variable, CFF and restricted faces remain external and are reported; font parts alone do not prove playback fidelity.

MiSans is not redistributed by this skill. Use a licensed installed/project-local copy for an exact match; otherwise the exporter discloses the substitution (Noto Sans SC for East Asian text, Liter for Latin-only text). Font selection uses decoded visible text, not comments, URLs or literal entity spellings. Source files are not rewritten during export.

## Selection principles

1. Language matching: when the user's query is in Chinese or a Chinese PPT deliverable is requested, both Chinese and English fonts need to be specified; otherwise, only English fonts need to be set
2. Selection approach: it is recommended to prioritize highly readable fonts for body text, and to use stylized fonts plus special treatments (all caps, widened letter spacing, bold, italics, etc.) in titles or special pages to strengthen the style
3. The font combination must support the overall visual style positioning
4. Name consistency: use a real family name, including its spaces. Historical aliases such as `HedvigLettersSans` and `QuattrocentoSans` are accepted and normalized. Non-RIBBI faces retain their own Windows family name: use `Coda ExtraBold` when that exact face is wanted rather than assuming it is `Coda` + `bold`.
5. Prefer bundled/local fonts for reproducibility. Review substitutions and unavailable styles against the brief; do not describe them as identical to a requested brand font.

## Font list

### English fonts

| Font name | Font type | Style and characteristics | Suitable scenarios | Stylized font |
|---|---|---|---|---|
| Liter | Sans-serif | Modern neo-grotesque style; low contrast, balanced proportions, optimized for screens; clean and rational | Tech, product | No |
| HedvigLettersSans | Sans-serif | A "non-designer perspective" design; slightly irregular with a distinctive personality and strong brand character | Creative design, branding | No |
| Oranienbaum | Serif | Modern high-contrast serif; strongly geometric with elegant lines and a classical temperament | Culture, art, fashion | No |
| QuattrocentoSans | Sans-serif | Classic, elegant sans-serif; gentle, highly readable, clear at small sizes | Academic, corporate, education | No |
| SortsMillGoudy | Serif | Revival of the classical print style of Goudy Old Style; soft serifs, pleasant to read | Literature, humanities | No |
| Unna | Serif | Neoclassical serif with a pronounced vertical rhythm; elegant yet forceful | Literature, publishing, academia | Yes |
| Coda | Sans-serif | Rounded and friendly; soft curves, high openness | Business, friendly brand tone | Yes |
| Jersey15 | Sans-serif (sports style) | Sports jersey style; squared structure with a noticeable grid feel (supports English + digits only) | Sports, tech showcase pages | Yes |
| Jersey20Charted | Pixel font (grid shading) | Sports-number style with a shaded grid that reinforces an athletic texture (supports English + digits only) | Sports, mechanical, decorative showcase pages | Yes |

### Chinese fonts

| Font name | Font type | Style and characteristics | Suitable scenarios | Usage restriction |
|---|---|---|---|---|
| MiSans | Sans-serif (heiti) | Xiaomi system font; clean and modern, variable weights, excellent on-screen rendering (multilingual support) | Tech, corporate, product | No |
| Noto Sans SC | Sans-serif (heiti) | A branch of Source Han Sans; well-regulated structure, neutral style, extremely broad coverage. Bundled as the portable CJK fallback; prefer an available requested brand font when appropriate. | Report-style | No |
| 思源宋体 | Serif (songti) | Source Han Serif; refined songti structure with stroke contrast; elegant reading experience (multilingual support) | Literature, design, formal presentations | No |
| 阿里妈妈刀隶体 | Calligraphy (clerical script) | Alimama DaoLi; clerical-script style with blade-like strokes; strength and archaic simplicity combined | China-chic, culture, art displays | No |
| 阿里妈妈东方大楷 | Calligraphy (regular script) | Alimama Dongfang Dakai; based on the Yan style of calligraphy; full and rounded, heavy and powerful | Culture, brand launches, guofeng (Chinese-style) themes | No |
| 阿里妈妈数黑体 | Sans-serif (heiti) | Alimama ShuHei; geometric heiti; uniform and regular with a strong commercial feel | Business, tech, e-commerce | No |
| 站酷文艺体 | Handwriting | Zcool WenYi; clean and fresh with a slight handwritten feel and a strong literary/artistic vibe | Light design, lifestyle | No |
| 飞波正点体 | Calligraphy (brush) | Feibo Zhengdian; brush-writing style with heavy strokes, full of power | Film posters, e-commerce, brand display | No |
| 得意黑 | Sans-serif (slanted heiti) | Smiley Sans; tall, slanted heiti combining humanist and geometric qualities with a strong modern feel. **Does not support a non-italic upright style** | Creative tech, brand display | No |
| 霞鹜新致宋 | Serif (songti) | LXGW XinZhiSong; based on IPAmj Mincho; bright, elegant, well-structured | Literature, classical style, print style | No |

### Mixed CJK–Latin fonts

| Font name | Font type | Style and characteristics | Suitable scenarios | Usage restriction |
|---|---|---|---|---|
| 精品点阵体 | Pixel font | Jingpin Dianzhen; 9×9 dot-matrix pixel style with an extremely retro electronic feel | Games, tech, pixel art | Yes |
| LXGW Bright | Serif (fangsong/kaiti) | LXGW WenKai family; combines fangsong and kaiti characteristics; gentle and clear letterforms | Literature, education, humanities | No |
| ZCOOL KuaiLe | Handwriting (rounded) | ZCOOL KuaiLe; lively, cute, playful and cartoonish; youthful energy | Anime, children, entertainment | No |

## Custom fonts and offline use

Labels of `heatmap` / `treemap` / `sunburst` / `sankey` charts are frozen as glyph outlines, so their font needs scalable monochrome outlines and regular-weight faces. Families that carry embedded bitmap strikes or color glyphs (for example SimSun, MS Gothic, Cambria) fail the export explicitly rather than being substituted; choose another family for those charts. Chart text styles take `color`, `fontSize` and `fontFamily` only.

Use custom fonts to fill missing categories (e.g. JetBrains Mono, Archivo Black or EB Garamond). `customFonts.src` accepts a project-relative TTF/TTC/OTF/EOT file or a Google Fonts CSS URL; the declared family must match the file's metadata. Local files stay inside the manifest directory. `--font-dir PATH` also searches explicitly supplied local font directories without declaring external project paths.

Google CSS uses a fixed non-browser user agent and must return one complete normal-weight TrueType face; text-specific and subset-only web responses are rejected. Downloads are cached outside the skill (`PPTD_FONT_CACHE` overrides the directory). `--offline` uses only local/bundled/cached fonts and local media. No browser, font installation, or runtime npm install is performed.

`--no-embed-fonts` deliberately leaves fonts external. Otherwise complete eligible faces are wrapped as valid EOT; RIBBI variants are bound under one family in regular/bold/italic/boldItalic order. Embedding does not permit redistributing loose system fonts. If a license prohibits editable outline embedding, or a variable/CFF face cannot be embedded, install that font on the intended rendering/playback machine and disclose the dependency.

When local Office is available, review the actual PPTX typography using `scripts/render_slides.py --if-available`. Native font names, style bindings and font-part integrity are separate from visual acceptance.
