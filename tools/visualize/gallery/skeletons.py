"""Compact starting points with the same routing and spacing as the full gallery."""

from .common import canvas, footer, text


def architecture():
    d = canvas(360, 480, "Layered architecture",
               "A minimal client, service, and database stack with aligned centers.",
               "Replace each layer with your component")
    client = d.node(80, 96, "Client", "browser / mobile", w=200)
    service = d.node(80, 208, "Service", "business logic", family="green", w=200)
    store = d.cylinder(80, 320, "Database", "persistent store", w=200)
    d.arrow(client.bottom, service.top, label="request", label_offset=12)
    d.arrow(service.bottom, store.top, color="green", label="query", label_offset=12)
    footer(d, [("neutral", "Client"), ("green", "Backend")])
    return d


def data_flow():
    d = canvas(640, 256, "Data flow scaffold",
               "Ingest raw events, transform them, and store the resulting batch.",
               "Name each stage and label the payload between stages")
    ingest = d.node(40, 112, "Ingest", "raw events", w=144)
    transform = d.node(248, 112, "Transform", "clean & enrich", family="green", w=144)
    store = d.node(456, 112, "Store", "write to sink", family="green", w=144)
    d.arrow(ingest.right, transform.left, label="stream", label_offset=12)
    d.arrow(transform.right, store.left, color="green", label="batch", label_offset=12)
    footer(d, [("neutral", "Ingest"), ("green", "Process / store")])
    return d


def flowchart():
    d = canvas(560, 560, "Decision scaffold",
               "Start, process, and check a condition. A successful result ends the flow; retry returns to processing.",
               "A decision with a complete retry path")
    start = d.node(184, 88, "Start", w=160)
    process = d.node(184, 184, "Process", "do work", w=160)
    decision = d.diamond(192, 296, "Valid?", hw=72, hh=40)
    done = d.node(64, 432, "Done", family="green", w=160)
    retry = d.node(336, 432, "Retry", family="terracotta", w=160)
    d.arrow(start.bottom, process.top)
    d.arrow(process.bottom, decision.top)
    d.lpath([decision.left, (done.cx, decision.cy), done.top], color="green", label="yes", label_offset=12)
    d.lpath([decision.right, (retry.cx, decision.cy), retry.top], color="terracotta", label="no", label_offset=12)
    d.lpath([retry.right, (520, retry.cy), (520, process.cy), process.right],
            color="terracotta", label="repeat", label_offset=-12)
    footer(d, [("amber", "Decision"), ("green", "Passed"), ("terracotta", "Retry")])
    return d


def sequence():
    d = canvas(520, 368, "Request and response",
               "Two participant lifelines exchange a request and a dashed response below the actor headers.",
               "Messages begin below the participant headers")
    client = d.lifeline(64, "Client", 96, 260, w=144)
    server = d.lifeline(312, "Server", 96, 260, family="green", w=144)
    d.arrow((client.x, 184), (server.x, 184), label="request", label_offset=12)
    d.arrow((server.x, 240), (client.x, 240), color="green", dashed=True, label="response", label_offset=12)
    footer(d, [("neutral", "Client"), ("green", "Server")],
           [("neutral", "Request", False), ("green", "Return", True)])
    return d


def comparison():
    d = canvas(520, 316, "Comparison scaffold",
               "A fictional two-by-two feature matrix with explicit yes and no labels.",
               "Keep the same scale across both options")
    for x, label in [(244, "Option A"), (408, "Option B")]:
        text(d, x, 98, label, size=14, anchor="middle")
    for index, cells in enumerate([
        [("Yes", "green"), ("No", "neutral")],
        [("No", "neutral"), ("Yes", "green")],
    ]):
        y = 124 + index * 56
        text(d, 40, y + 20, f"Feature {index + 1}")
        for x, (value, family) in zip((172, 336), cells):
            d.bar(x, y, 144, value, family=family, h=40)
    footer(d, [("green", "Supported"), ("neutral", "Unavailable")])
    return d


def state_machine():
    d = canvas(520, 208, "State lifecycle",
               "An initial state starts processing; a finish event reaches the final state. Arrows stop at the circle boundaries.",
               "One state between initial and final markers")
    d.state_dot(64, 132)
    active = d.state(180, 104, "Active", "processing", w=160)
    d.state_dot(456, 132, kind="final")
    d.arrow((72, 132), active.left, label="start", label_offset=12)
    d.arrow(active.right, (444, 132), label="finish", label_offset=12)
    return d
