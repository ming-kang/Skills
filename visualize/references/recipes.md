# Fast recipes — copy, adjust, save

Open this file **only** when the request matches a domain shortcut or you want a ready skeleton. Keep `SKILL.md` as the entry point; do not also load the full cookbook unless you need a shape that is not here.

Assumes `svgkit` is importable (see bootstrap in `SKILL.md`). Each block is complete.

---

## 1. Linear pipeline (default fast path)

```python
d = Diagram(760, 200, title="Pipeline", desc="Stages left to right.")
d.pipeline([
    {"title": "In", "sub": "source"},
    {"title": "Process", "sub": "transform", "family": "green"},
    {"title": "Out", "sub": "result", "family": "purple"},
], labels=[None, "payload"], auto_legend=True)
d.save("pipeline.svg")
```

Tint siblings in one family instead of new colors:

```python
d.pipeline([
    {"title": "Stage A", "family": "green", "opacity": 0.9},
    {"title": "Stage B", "family": "green", "opacity": 0.55},
    {"title": "Stage C", "family": "green", "opacity": 0.4},
])
d.save("stages.svg")
```

---

## 2. RAG pipeline

```python
d = Diagram(880, 220, title="RAG pipeline", desc="Query to grounded answer.")
d.pipeline([
    {"title": "Query", "sub": "user question"},
    {"title": "Embed", "sub": "to vector"},
    {"title": "Retrieve", "sub": "top-k", "family": "green"},
    {"title": "LLM", "sub": "grounded answer", "family": "purple"},
    {"title": "Response", "sub": "to user"},
], labels=["embed", "vector", "context", None],
   legend=[("green", "retrieval"), ("purple", "generation")])
d.save("rag-pipeline.svg")
```

Gallery feel: `assets/gallery/data-flow.svg`, `assets/samples/hero.svg`.

---

## 3. Vertical stack (col + chain)

```python
d = Diagram(320, 400, title="Request path", desc="Top-down service call.")
boxes = d.col([
    {"title": "Client"},
    {"title": "API", "family": "green"},
    {"title": "DB", "sub": "postgres", "family": "purple"},
], x=80, y=40, gap=56)
d.chain(boxes)
d.save("request-path.svg")
```

---

## 4. Fan-out (orchestrator → workers)

```python
d = Diagram(720, 320, title="Multi-agent", desc="Orchestrator fans out to specialists.")
orch = d.node(300, 40, "Orchestrator", sub="planner", family="amber")
workers = d.row([
    {"title": "Research", "family": "green"},
    {"title": "Code", "family": "purple"},
    {"title": "Review", "family": "terracotta"},
], x=40, y=160, gap=48)
d.fanout(orch, workers)
d.auto_legend()
d.save("multi-agent.svg")
```

---

## 5. Architecture layers (row bands)

```python
d = Diagram(720, 420, title="Architecture", desc="Client to data.")
d.container(40, 40, 640, 80, label="Client")
d.row([{"title": "Web"}, {"title": "Mobile"}], x=80, y=56, gap=40)

d.container(40, 140, 640, 100, label="Services")
svc = d.row([
    {"title": "Gateway", "family": "green"},
    {"title": "User", "family": "green"},
    {"title": "Order", "family": "green"},
], x=60, y=172, gap=40)

d.container(40, 260, 640, 100, label="Data")
stores = [
    d.cylinder(100, 288, "Postgres", family="purple"),
    d.cylinder(320, 288, "Redis", family="purple"),
]
d.connect(svc[0], svc[1])
d.connect(svc[1], svc[2])
d.connect(svc[1], stores[0])
d.connect(svc[2], stores[1])
d.legend([("green", "services"), ("purple", "stores")])
d.save("architecture.svg")
```

Prefer adapting `assets/gallery/architecture.svg` for dense layouts.

---

## 6. Decision diamond (flowchart)

```python
d = Diagram(520, 360, title="Auth check", desc="Allow or deny.")
start = d.node(200, 40, "Request")
dec = d.diamond(180, 140, "Valid?", family="amber")
ok = d.node(40, 280, "Allow", family="green")
no = d.node(320, 280, "Deny", family="terracotta")
d.connect(start, dec)
d.connect(dec, ok, label="yes", color="green")
d.connect(dec, no, label="no", color="terracotta")
d.auto_legend()
d.save("auth-check.svg")
```

Gallery: `assets/gallery/flowchart.svg`.

---

## 7. Sequence (lifelines)

```python
d = Diagram(560, 320, title="Checkout", desc="Client calls API then DB.")
c = d.lifeline(80, "Client", 40, 280)
a = d.lifeline(260, "API", 40, 280, family="green")
db = d.lifeline(440, "DB", 40, 280, family="purple")
# Messages: edge of actor boxes → points on lifelines
d.arrow(c.actor.bottom, (a.x, 100), label="POST /pay", color="green")
d.arrow((a.x, 140), (db.x, 140), label="INSERT", color="purple")
d.arrow((db.x, 180), (a.x, 180), label="ok", dashed=True)
d.arrow((a.x, 220), (c.x, 220), label="200", dashed=True)
d.save("checkout-seq.svg")
```

Gallery: `assets/gallery/sequence.svg`.

---

## 8. Comparison grid

```python
d = Diagram(640, 280, title="Options", desc="Feature comparison.")
d.heading("Build vs buy")
grid = d.grid([
    [{"title": "", "w": 120}, {"title": "Build", "w": 140}, {"title": "Buy", "w": 140}],
    [{"title": "Cost", "w": 120}, {"title": "High", "family": "terracotta", "w": 140},
     {"title": "Low", "family": "green", "w": 140}],
    [{"title": "Control", "w": 120}, {"title": "Full", "family": "green", "w": 140},
     {"title": "Partial", "family": "amber", "w": 140}],
], x=40, y=64, gap_x=24, gap_y=20)
d.save("comparison.svg")
```

For full matrix cells, prefer `assets/gallery/comparison.svg` + `.raw()` cells.

---

## Tips

- **Fewer files open = faster.** Recipes + `pipeline` cover most user asks.
- **Validate quietly:** `python3 scripts/validate_svg.py -q out.svg`
- **Wrong family name** now raises a clear `KeyError` listing valid families.
- Need a shape not listed here → gallery SVG for that type, then `svg-cookbook.md` §0.
