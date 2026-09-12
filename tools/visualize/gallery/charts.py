"""Comparison matrix and timeline reference layouts."""

from .common import canvas, footer, rule, text


def comparison():
    d = canvas(760, 432, "Feature coverage",
               "Three fictional product profiles are compared on four features. Cell labels distinguish supported, planned, and unavailable features.",
               "Fictional profiles; each cell shows a feature's availability")
    columns = [(208, "Profile A"), (384, "Profile B"), (560, "Profile C")]
    for x, label in columns:
        text(d, x + 80, 102, label, size=14, anchor="middle")
    rows = [
        ("CSV export", [("Yes", "green"), ("Yes", "green"), ("Planned", "amber")]),
        ("Offline mode", [("No", "neutral"), ("Yes", "green"), ("No", "neutral")]),
        ("Audit log", [("Planned", "amber"), ("No", "neutral"), ("Yes", "green")]),
        ("API access", [("Yes", "green"), ("Planned", "amber"), ("Yes", "green")]),
    ]
    for index, (label, values) in enumerate(rows):
        y = 132 + index * 56
        text(d, 184, y + 20, label, anchor="end")
        for (x, _), (value, family) in zip(columns, values):
            d.bar(x, y, 160, value, family=family, h=40)
    footer(d, [("green", "Supported"), ("amber", "Planned"), ("neutral", "Unavailable")])
    return d


def timeline_gantt():
    d = canvas(800, 504, "Product launch · 6 weeks",
               "Design spans weeks 1–2, development weeks 2–4, testing weeks 4–5, and launch week 6. Milestones mark design freeze and release.",
               "Overlapping phases with explicit release milestones")
    axis_x, week = 200, 88
    text(d, 40, 96, "Phase")
    for index in range(7):
        x = axis_x + week * index
        d.raw(f'<line x1="{x}" y1="112" x2="{x}" y2="368" '
              'stroke="rgba(31,30,29,0.3)" stroke-width="0.5" stroke-dasharray="4 3"/>', layer="containers")
        if index < 6:
            text(d, x + week / 2, 96, f"W{index + 1}", anchor="middle")
    rule(d, 40, 112, 760)
    phases = [
        ("Design", 0, 2, "Prototype"),
        ("Develop", 1, 3, "Build + integrate"),
        ("Test", 3, 2, "Verify"),
        ("Launch", 5, 1, "Rollout"),
    ]
    for index, (label, start, duration, detail) in enumerate(phases):
        y = 144 + index * 64
        text(d, 40, y + 14, label, size=14)
        d.bar(axis_x + start * week, y, duration * week, detail, family="green")
    for end_week, label in [(2, "Design freeze"), (6, "Release")]:
        x = axis_x + end_week * week
        text(d, x, 388, label, family="amber", anchor="middle")
        d.diamond(x - 8, 400, "", hw=8, hh=8)
    footer(d, [("green", "Work phase"), ("amber", "Milestone")])
    return d
