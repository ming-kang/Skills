"""Reusable explanatory layouts distilled from the supplied SVG references."""

from svgkit import FAMILIES, snap

from .common import canvas, footer, rail, rule, text


def leader(d, points):
    """A light, undirected annotation link, distinct from a process arrow."""
    route = "M" + " L".join(f"{snap(x)} {snap(y)}" for x, y in points)
    d.raw(f'<path data-role="decoration" d="{route}" fill="none" '
          'stroke="#73726C" stroke-width="0.75" stroke-dasharray="3 3"/>', layer="arrows")


def feedback_pipeline():
    d = canvas(800, 648, "Review and release",
               "Draft, build, review, and release form a vertical spine. Rejected work returns to the draft through a separate revision gutter. A sidebar lists the review criteria.",
               "A clear forward path, a separate revision loop, and a local explanation")
    draft = d.node(128, 104, "Draft", "describe the change", w=288)
    build = d.node(128, 216, "Build", "prepare the artifact", w=288)
    review = d.node(128, 328, "Review", "check against the criteria", family="amber", w=288)
    release = d.node(128, 440, "Release", "publish the accepted artifact", family="green", w=288)
    d.arrow(draft.bottom, build.top)
    d.arrow(build.bottom, review.top)
    d.arrow(review.bottom, release.top, color="green", label="accepted", label_offset=12)
    d.lpath([review.left, (56, review.cy), (56, draft.cy), draft.left],
            color="terracotta", dashed=True, label="revise", label_offset=12)
    d.panel(512, 280, 248, 184, "Review criteria", family="amber")
    for y, label in [(332, "Correct behavior"), (364, "Readable output"),
                     (396, "Complete records"), (428, "Reproducible checks")]:
        text(d, 532, y, label)
    leader(d, [review.right, (464, review.cy), (512, 356)])
    text(d, 128, 552, "Rejected work returns to draft; accepted work moves to release.")
    footer(d, [("neutral", "Work"), ("amber", "Review"), ("green", "Accepted")],
           [("neutral", "Forward", False), ("terracotta", "Revise", True)])
    return d


def annotated_funnel():
    d = canvas(800, 688, "Record retention",
               "An illustrative batch contains 1,000 records. Required-field checks retain 800, schema checks retain 600, and deduplication retains 480. Band widths are proportional to retained counts; adjacent notes explain each reduction.",
               "Illustrative counts · band width shows records retained after each check")
    stages = [("Received", 1000, "neutral"), ("Complete", 800, "green"),
              ("Valid", 600, "green"), ("Unique", 480, "green")]
    bands = []
    for index, (label, count, family) in enumerate(stages):
        width, y = 400 * count / 1000, 104 + index * 128
        x = 280 - width / 2
        fam = FAMILIES[family]
        if bands:
            px, py, pw = bands[-1]
            points = f"{px},{py + 64} {px + pw},{py + 64} {x + width},{y} {x},{y}"
            d.raw(f'<polygon data-role="data-mark" points="{points}" '
                  'fill="#E1F5EE" fill-opacity="0.6"/>', layer="containers")
        d.raw(f'<rect data-role="data-mark" x="{x}" y="{y}" width="{width}" height="64" '
              f'rx="6" fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>')
        text(d, 280, y + 24, label, size=14, family=family, anchor="middle", role="node-text")
        text(d, 280, y + 44, f"{count:,} records · {count / 10:g}%", family=family,
             anchor="middle", role="node-text")
        bands.append((x, y, width))
    d.node(520, 104, "Sample batch", "fictional input counts", w=240, h=64)
    for index, (removed, reason) in enumerate([
        (200, "required fields absent"), (200, "schema mismatch"), (120, "duplicate records"),
    ], 1):
        x, y, width = bands[index]
        d.node(520, y, f"{removed} removed", reason, w=240, h=64)
        leader(d, [(x + width, y + 32), (520, y + 32)])
    text(d, 80, 600, "Each count refers to the retained batch; removals are relative to the prior stage.")
    footer(d, [("neutral", "Input / explanation"), ("green", "Retained records")])
    return d


def parallel_pipelines():
    d = canvas(800, 752, "Build one revision for two platforms",
               "One source package fans out into Linux and Windows pipelines. Each pipeline compiles, tests, and packages that same revision. Both platform packages are collected as release artifacts.",
               "Shared input, aligned stages, and an explicit merge of the outputs")
    source = d.node(272, 96, "Source package", "one version", w=256)
    rail(d, [source.bottom, (source.cx, 180)])
    outputs = []
    for x, family, label in [(40, "green", "Linux"), (424, "purple", "Windows")]:
        d.panel(x, 200, 336, 336, label, family=family)
        nodes = [d.node(x + 40, y, title, sub, family=family, w=256)
                 for y, title, sub in [(252, "Compile", "target platform"),
                                        (356, "Run tests", "required suites"),
                                        (460, "Package", "build artifacts")]]
        d.lpath([(source.cx, 180), (nodes[0].cx, 180), nodes[0].top], color=family)
        for first, second in zip(nodes, nodes[1:]):
            d.arrow(first.bottom, second.top, color=family)
        outputs.append(nodes[-1])
    result = d.node(272, 584, "Release artifacts", "both platform packages", w=256)
    for output in outputs:
        rail(d, [output.bottom, (output.cx, 556)])
    rail(d, [(outputs[0].cx, 556), (outputs[1].cx, 556)])
    d.arrow((result.cx, 556), result.top)
    footer(d, [("neutral", "Shared artifact"), ("green", "Linux pipeline"), ("purple", "Windows pipeline")])
    return d


def mechanism_comparison():
    d = canvas(800, 640, "同一组数据，两种求和方式",
               "对输入 2、4、3，批量方式保留全部值后求和；逐项方式将累计值从 0 更新为 2、6、9。两种方式的最终总和都为 9。",
               "输入为 2、4、3；并列展示处理机制和保留的数据")
    for x, family, title in [(40, "green", "批量求和"), (424, "purple", "逐项累加")]:
        d.panel(x, 104, 336, 336, title, family=family)
        fam = FAMILIES[family]
        for offset, value in zip((72, 168, 264), (2, 4, 3)):
            cx = x + offset
            d.raw(f'<circle data-role="data-mark" cx="{cx}" cy="176" r="18" '
                  f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>')
            text(d, cx, 176, str(value), size=14, family=family, anchor="middle", role="node-text")
    batch = d.node(80, 240, "保留全部输入", "2 · 4 · 3", family="green", w=256)
    for cx in (112, 208, 304):
        d.arrow((cx, 194), (cx, 240), color="green")
    batch_sum = d.node(104, 352, "总和 = 9", "收到所有值后计算", family="green", w=208)
    d.arrow(batch.bottom, batch_sum.top, color="green")
    states = [d.node(x, 240, str(value), calculation, family="purple", w=80)
              for x, value, calculation in [(456, 2, "0 + 2"), (552, 6, "2 + 4"), (648, 9, "6 + 3")]]
    for state in states:
        d.arrow((state.cx, 194), state.top, color="purple")
    for first, second in zip(states, states[1:]):
        d.arrow(first.right, second.left, color="purple")
    running_sum = d.node(488, 352, "总和 = 9", "每次只更新当前总和", family="purple", w=208)
    d.lpath([states[-1].bottom, (states[-1].cx, 328), (running_sum.cx, 328), running_sum.top], color="purple")
    rule(d, 40, 464, 760)
    for y, dimension, left, right in [(492, "处理时保留", "全部输入值", "当前累计值"),
                                     (532, "更新时机", "收齐后计算", "每收到一个值")]:
        text(d, 40, y, dimension)
        text(d, 208, y, left, anchor="middle")
        text(d, 592, y, right, anchor="middle")
    footer(d, [("green", "批量方式"), ("purple", "逐项方式")])
    return d


def annotated_chart():
    d = canvas(800, 512, "Retry delay by attempt",
               "An illustrative retry schedule uses delays of 1, 2, 4, 8, and 8 seconds across attempts 1 through 5. Linear axes and a local callout identify the eight-second cap.",
               "Illustrative schedule · linear axes · seconds")
    left, right, top, bottom = 96, 560, 128, 368
    text(d, left, 96, "Delay (s)")
    for value in range(0, 11, 2):
        y = bottom - value * 24
        rule(d, left, y, right)
        text(d, 80, y, str(value), anchor="end")
    d.raw(f'<path data-role="decoration" d="M{left} {top} V{bottom} H{right}" '
          'fill="none" stroke="#73726C" stroke-width="0.75"/>', layer="containers")
    points = [(left + index * 116, bottom - value * 24) for index, value in enumerate((1, 2, 4, 8, 8))]
    route = " ".join(f"{x},{y}" for x, y in points)
    d.raw(f'<polyline data-role="data-mark" points="{route}" fill="none" '
          'stroke="#1D9E75" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
    for attempt, (x, y) in enumerate(points, 1):
        d.raw(f'<circle data-role="data-mark" cx="{x}" cy="{y}" r="4" fill="#1D9E75"/>')
        text(d, x, 392, str(attempt), anchor="middle")
    text(d, (left + right) / 2, 420, "Attempt", anchor="middle")
    d.panel(608, 144, 152, 112, "8 s cap", family="green")
    text(d, 628, 196, "Attempts 4–5")
    text(d, 628, 224, "same delay")
    leader(d, [points[-1], (608, points[-1][1])])
    rule(d, 40, 448, 760, layer="legend")
    d.raw('<line x1="40" y1="472" x2="70" y2="472" stroke="#1D9E75" stroke-width="1.5"/>', layer="legend")
    d.raw('<circle data-role="data-mark" cx="55" cy="472" r="4" fill="#1D9E75"/>', layer="legend")
    text(d, 82, 472, "Scheduled delay", role="legend-label", layer="legend")
    return d


def quadrant_map():
    d = canvas(760, 616, "Prioritizing maintenance work",
               "A qualitative two-axis map groups maintenance work by impact and effort. The four regions distinguish quick wins, projects, small fixes, and work needing a scope review. Positions are categories, not measured scores.",
               "Qualitative map · categories, not measured positions")
    quadrants = [
        (144, 112, "Quick wins", "green", ["Small change", "Broad benefit"]),
        (432, 112, "Plan a project", "amber", ["Larger change", "Broad benefit"]),
        (144, 320, "Batch small fixes", "neutral", ["Small change", "Narrow benefit"]),
        (432, 320, "Review the scope", "terracotta", ["Larger change", "Narrow benefit"]),
    ]
    for x, y, title, family, lines in quadrants:
        fam = FAMILIES[family]
        d.raw(f'<rect data-role="panel" x="{x}" y="{y}" width="248" height="176" rx="8" '
              f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>', layer="containers")
        text(d, x + 20, y + 32, title, size=14, family=family, role="container-label")
        for index, label in enumerate(lines):
            text(d, x + 20, y + 76 + 32 * index, label, family=family, role="container-label")
    d.arrow((128, 512), (128, 96))
    d.arrow((128, 512), (704, 512))
    text(d, 48, 96, "Impact")
    text(d, 112, 200, "High", anchor="end")
    text(d, 112, 408, "Low", anchor="end")
    text(d, 268, 532, "Low effort", anchor="middle")
    text(d, 556, 532, "High effort", anchor="middle")
    footer(d, [("green", "Quick win"), ("amber", "Project"), ("neutral", "Small fix"), ("terracotta", "Review scope")])
    return d
