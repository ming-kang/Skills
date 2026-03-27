#!/usr/bin/env python
"""
Background Example - DO NOT COPY, create your own design.

Learn: HTML/CSS techniques (radial-gradient, positioning, transparency), Playwright workflow.
Do NOT copy: colors, layout, this specific aesthetic.

Design Directions (pick one, then create original):

  Universal:
    Swiss Grid / Minimalist / Double Border / Clean Whitespace
    Soft Blocks / Gradient Ribbons / Frosted Glass / Subtle Grid
    Watercolor Wash / Ink Wash / Line Art / Grain Texture

  Expressive (match scenario well = stunning; mismatch = distracting):
    Bauhaus Geometric / Memphis / Art Deco / Monochrome Bold

Technical: 794×1123px, device_scale_factor=2, center clear for text, low saturation.
"""
import os
import sys


def print_usage():
    script_name = os.path.basename(sys.argv[0])
    print(f"Usage: python {script_name} [output-dir]")
    print("Generates local PNG background assets for cover, back cover, and body pages.")
    print("Output directory: explicit [output-dir], DOCX_ASSET_OUTPUT_DIR, or the current working directory.")
    print("Dependencies: playwright + Chromium (`python -m playwright install chromium`).")
    print("Local PNG assets are working files, not shipped skill outputs.")


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Missing dependency for background asset generation: playwright", file=sys.stderr)
        print("Install it with: python -m pip install playwright", file=sys.stderr)
        print("Then install Chromium with: python -m playwright install chromium", file=sys.stderr)
        raise SystemExit(1)

    return sync_playwright

def resolve_output_dir():
    if len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help", "help"):
        return os.path.abspath(sys.argv[1])

    env_dir = os.environ.get("DOCX_ASSET_OUTPUT_DIR")
    if env_dir:
        return os.path.abspath(env_dir)

    return os.getcwd()


OUTPUT_DIR = resolve_output_dir()

PAGE_W = 794
PAGE_H = 1123

# Morandi Color Palette
MORANDI = {
    'green': '#7C9885',
    'blue': '#8B9DC3',
    'beige': '#B4A992',
    'rose': '#C9A9A6',
    'sage': '#9CAF88',
}

# ============================================================================
# Cover - Color block gradient, no frames
# ============================================================================
COVER_BG_HTML = f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: {PAGE_W}px;
    height: {PAGE_H}px;
    background: linear-gradient(160deg, #f8faf9 0%, #f0f4f2 100%);
    position: relative;
    overflow: hidden;
}}

/* Top-right large blob */
.blob-1 {{
    position: absolute;
    top: -120px;
    right: -150px;
    width: 550px;
    height: 550px;
    background: radial-gradient(ellipse at center,
        {MORANDI['green']}50 0%,
        {MORANDI['green']}25 40%,
        transparent 70%
    );
    border-radius: 50%;
}}

/* Bottom-left blob */
.blob-2 {{
    position: absolute;
    bottom: -150px;
    left: -120px;
    width: 600px;
    height: 600px;
    background: radial-gradient(ellipse at center,
        {MORANDI['blue']}40 0%,
        {MORANDI['blue']}18 45%,
        transparent 70%
    );
    border-radius: 50%;
}}

/* Center-right blob */
.blob-3 {{
    position: absolute;
    top: 35%;
    right: 5%;
    width: 350px;
    height: 350px;
    background: radial-gradient(ellipse at center,
        {MORANDI['beige']}35 0%,
        transparent 60%
    );
    border-radius: 50%;
}}

/* Top accent bar */
.accent-bar {{
    position: absolute;
    top: 60px;
    left: 60px;
    width: 140px;
    height: 6px;
    background: linear-gradient(90deg, {MORANDI['green']}, {MORANDI['sage']});
    border-radius: 3px;
}}

/* Bottom-right corner accent */
.corner-accent {{
    position: absolute;
    bottom: 50px;
    right: 50px;
    width: 90px;
    height: 90px;
    border: 2.5px solid {MORANDI['green']}40;
    border-radius: 50%;
}}

.corner-accent::after {{
    content: '';
    position: absolute;
    top: 18px;
    left: 18px;
    width: 54px;
    height: 54px;
    background: {MORANDI['green']}20;
    border-radius: 50%;
}}
</style>
</head>
<body>
    <div class="blob-1"></div>
    <div class="blob-2"></div>
    <div class="blob-3"></div>
    <div class="accent-bar"></div>
    <div class="corner-accent"></div>
</body>
</html>
'''

# ============================================================================
# Back Cover - Echo cover, mirrored positioning
# ============================================================================
BACKCOVER_BG_HTML = f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: {PAGE_W}px;
    height: {PAGE_H}px;
    background: linear-gradient(200deg, #f8faf9 0%, #f0f4f2 100%);
    position: relative;
    overflow: hidden;
}}

/* Bottom-left blob - echo cover top-right */
.blob-1 {{
    position: absolute;
    bottom: -120px;
    left: -150px;
    width: 500px;
    height: 500px;
    background: radial-gradient(ellipse at center,
        {MORANDI['green']}45 0%,
        {MORANDI['green']}20 40%,
        transparent 70%
    );
    border-radius: 50%;
}}

/* Top-right blob - echo cover bottom-left */
.blob-2 {{
    position: absolute;
    top: -100px;
    right: -80px;
    width: 400px;
    height: 400px;
    background: radial-gradient(ellipse at center,
        {MORANDI['blue']}35 0%,
        transparent 65%
    );
    border-radius: 50%;
}}

/* Top accent */
.top-accent {{
    position: absolute;
    top: 60px;
    right: 60px;
    width: 120px;
    height: 5px;
    background: linear-gradient(90deg, {MORANDI['sage']}, {MORANDI['green']});
    border-radius: 2px;
}}

/* Bottom-left corner accent */
.corner-accent {{
    position: absolute;
    bottom: 50px;
    left: 50px;
    width: 70px;
    height: 70px;
    border: 2px solid {MORANDI['green']}35;
    border-radius: 50%;
}}
</style>
</head>
<body>
    <div class="blob-1"></div>
    <div class="blob-2"></div>
    <div class="top-accent"></div>
    <div class="corner-accent"></div>
</body>
</html>
'''

# ============================================================================
# Body - More noticeable decoration, but doesn't interfere with reading
# ============================================================================
BODY_BG_HTML = f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: {PAGE_W}px;
    height: {PAGE_H}px;
    background: #FDFEFE;
    position: relative;
    overflow: hidden;
}}

/* Top gradient band - more noticeable */
.top-gradient {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 120px;
    background: linear-gradient(180deg,
        {MORANDI['green']}12 0%,
        {MORANDI['green']}04 60%,
        transparent 100%
    );
}}

/* Left side bar - thicker and longer */
.side-bar {{
    position: absolute;
    top: 0;
    left: 0;
    width: 5px;
    height: 100%;
    background: linear-gradient(180deg,
        {MORANDI['green']}30 0%,
        {MORANDI['green']}15 30%,
        {MORANDI['green']}08 60%,
        transparent 100%
    );
}}

/* Bottom-right subtle decoration */
.corner-blob {{
    position: absolute;
    bottom: -80px;
    right: -80px;
    width: 200px;
    height: 200px;
    background: radial-gradient(ellipse at center,
        {MORANDI['blue']}08 0%,
        transparent 70%
    );
    border-radius: 50%;
}}
</style>
</head>
<body>
    <div class="top-gradient"></div>
    <div class="side-bar"></div>
    <div class="corner-blob"></div>
</body>
</html>
'''


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print_usage()
        return

    sync_playwright = load_playwright()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            print("Chromium is required for background asset generation.", file=sys.stderr)
            print("Install it with: python -m playwright install chromium", file=sys.stderr)
            raise SystemExit(1)
        page = browser.new_page(
            viewport={'width': PAGE_W, 'height': PAGE_H},
            device_scale_factor=2
        )

        page.set_content(COVER_BG_HTML)
        page.screenshot(path=os.path.join(OUTPUT_DIR, 'cover_bg.png'), type='png')
        print(f"cover_bg.png -> {OUTPUT_DIR}")

        page.set_content(BACKCOVER_BG_HTML)
        page.screenshot(path=os.path.join(OUTPUT_DIR, 'backcover_bg.png'), type='png')
        print(f"backcover_bg.png -> {OUTPUT_DIR}")

        page.set_content(BODY_BG_HTML)
        page.screenshot(path=os.path.join(OUTPUT_DIR, 'body_bg.png'), type='png')
        print(f"body_bg.png -> {OUTPUT_DIR}")

        browser.close()
    print("Done - Morandi (no glass frames)")


if __name__ == '__main__':
    main()
