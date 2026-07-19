#!/usr/bin/env python3
"""One-shot gallery / sample quality regeneration. Run from repo root or this dir."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent  # visualize/
sys.path.insert(0, str(SCRIPTS))

from svgkit import Diagram  # noqa: E402

G = ROOT / "assets" / "gallery"
S = ROOT / "assets" / "samples"


def mind_map() -> None:
    d = Diagram(
        800, 420,
        title="AI agent capability map",
        desc="Five core agent capabilities radiating from a central node: "
             "perception, memory, reasoning, action, and learning.",
    )
    hub = d.node(325, 180, "AI agent", "core loop", family="purple", w=150)
    perc = d.node(325, 40, "Perception", family="green", w=150, h=40)
    mem = d.node(590, 100, "Memory", family="green", w=150, h=40)
    reason = d.node(590, 260, "Reasoning", family="amber", w=150, h=40)
    action = d.node(100, 260, "Action", family="amber", w=150, h=40)
    learn = d.node(100, 100, "Learning", family="green", w=150, h=40)
    d.curve(hub.top, perc.bottom, color="green", marker=False)
    d.curve(hub.right, mem.left, color="green", marker=False)
    d.curve(hub.right, reason.left, color="amber", marker=False)
    d.curve(hub.left, action.right, color="amber", marker=False)
    d.curve(hub.left, learn.right, color="green", marker=False)
    d.legend([
        ("purple", "core"),
        ("green", "sense / memory"),
        ("amber", "act / reason"),
    ])
    d.save(str(G / "mind-map.svg"))
    print("mind-map", d.width, d.height)


def architecture() -> None:
    d = Diagram(
        760, 540,
        title="Microservice architecture",
        desc="Client traffic enters through an API gateway, fans out to three "
             "services, which persist to a relational store and a cache.",
    )
    client = d.node(320, 40, "Client", "web + mobile")
    gw = d.node(310, 140, "API gateway", "routing + auth", family="green")
    d.container(40, 250, 680, 100, label="Services")
    user = d.node(70, 280, "User service", "accounts", family="green")
    order = d.node(290, 280, "Order service", "checkout", family="green")
    pay = d.node(520, 280, "Payment service", "billing", family="amber")
    pg = d.cylinder(170, 410, "PostgreSQL", "orders + users", family="purple")
    redis = d.cylinder(420, 410, "Redis", "session cache", family="purple")
    d.connect(client, gw)
    d.fanout(gw, [user, order, pay], gutter=30)
    rail = 380
    d.lpath([user.bottom, (user.cx, rail), (pg.cx, rail), pg.top], color="purple")
    d.lpath([order.bottom, (order.cx, rail), (pg.cx, rail)], color="purple")
    d.lpath([pay.bottom, (pay.cx, rail), (redis.cx, rail), redis.top], color="purple")
    d.legend([
        ("green", "services"),
        ("amber", "payment"),
        ("purple", "stores"),
    ])
    d.save(str(G / "architecture.svg"))
    print("architecture", d.width, d.height)


def flowchart() -> None:
    d = Diagram(
        720, 560,
        title="Pre-deploy quality gate",
        desc="A change passes review and tests; a failing test routes back to "
             "fixes, a passing one proceeds to deploy.",
    )
    pr = d.node(300, 40, "Open PR", "diff ready", family="green")
    rev = d.node(300, 140, "Code review", "human + lint")
    dec = d.diamond(260, 240, "Tests pass?", family="amber", hh=50)
    fix = d.node(540, 260, "Fix issues", "amend diff", family="terracotta")
    dep = d.node(300, 420, "Deploy", "ship to prod", family="green")
    d.connect(pr, rev, color="green")
    d.connect(rev, dec)
    d.connect(dec, fix, color="terracotta", label="no")
    d.lpath(
        [
            fix.top,
            (fix.cx, 212),
            (rev.x + rev.w + 40, 212),
            (rev.x + rev.w + 40, rev.cy),
            rev.right,
        ],
        color="terracotta",
    )
    d.connect(dec, dep, color="green", label="yes")
    d.legend([
        ("green", "pass path"),
        ("amber", "decision"),
        ("terracotta", "fail / retry"),
    ])
    d.save(str(G / "flowchart.svg"))
    print("flowchart", d.width, d.height)


def comparison() -> None:
    d = Diagram(
        720, 340,
        title="RAG vs fine-tuning vs prompting",
        desc="A feature matrix comparing three approaches across setup cost, "
             "latency, freshness, and control.",
    )
    for i, name in enumerate(["RAG", "Fine-tune", "Prompt"]):
        d.raw(
            f'<text x="{280 + i * 160}" y="54" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="#141413">{name}</text>',
            layer="labels",
        )
    for i, name in enumerate(["Setup cost", "Latency", "Freshness", "Control"]):
        d.raw(
            f'<text x="188" y="{96 + i * 52}" text-anchor="end" '
            f'dominant-baseline="central" font-size="12" fill="#3D3D3A">'
            f'{name}</text>',
            layer="labels",
        )
    cells = [
        [("Low", "green"), ("High", "terracotta"), ("Low", "green")],
        [("Med", "amber"), ("Low", "green"), ("Low", "green")],
        [("High", "green"), ("Low", "terracotta"), ("Med", "amber")],
        [("Med", "amber"), ("High", "green"), ("Low", "terracotta")],
    ]
    for r, row in enumerate(cells):
        for c, (lab, fam) in enumerate(row):
            d.node(206 + c * 160, 76 + r * 52, lab, family=fam, w=148, h=40)
    d.legend([
        ("green", "good"),
        ("amber", "mixed"),
        ("terracotta", "poor"),
    ])
    d.save(str(G / "comparison.svg"))
    print("comparison", d.width, d.height)


def network() -> None:
    d = Diagram(
        760, 460,
        title="Three-tier network topology",
        desc="Internet traffic passes a firewall into a DMZ core switch "
             "serving two app servers.",
    )
    inet = d.node(320, 40, "Internet", "public WAN", family="green")
    fw = d.node(316, 130, "Firewall", "ingress filter", family="terracotta")
    d.container(180, 210, 400, 190, label="DMZ", sub="demilitarized zone")
    sw = d.node(290, 250, "Core switch", "L3 routing")
    a = d.node(210, 330, "App server A", "10.0.1.10", family="purple")
    b = d.node(430, 330, "App server B", "10.0.1.11", family="purple")
    d.connect(inet, fw, color="green", label="HTTPS")
    d.connect(fw, sw)
    d.fanout(sw, [a, b], color="purple")
    d.legend([
        ("green", "external"),
        ("terracotta", "firewall"),
        ("neutral", "core"),
        ("purple", "internal hosts"),
    ])
    d.save(str(G / "network-topology.svg"))
    print("network", d.width, d.height)


def sequence() -> None:
    d = Diagram(
        900, 480,
        title="OAuth2 authorization code flow",
        desc="The client redirects the user to the auth server, exchanges the "
             "code for a token, then calls the resource server.",
    )
    user = d.lifeline(80, "User", 40, 420, family="green")
    client = d.lifeline(280, "Client", 40, 420)
    auth = d.lifeline(500, "Auth server", 40, 420, family="purple")
    res = d.lifeline(720, "Resource", 40, 420, family="amber")
    # messages on lifelines
    d.arrow((user.x, 130), (auth.x, 130), color="purple", label="authorize")
    d.arrow((auth.x, 180), (user.x, 180), dashed=True, label="login + consent")
    d.arrow((user.x, 230), (client.x, 230), color="green", label="auth code")
    d.arrow((client.x, 280), (auth.x, 280), color="purple", label="exchange")
    d.arrow((auth.x, 330), (client.x, 330), color="green", dashed=True, label="token")
    d.arrow((client.x, 380), (res.x, 380), color="amber", label="API call")
    d.arrow((res.x, 420), (client.x, 420), dashed=True, label="resource")
    d.legend([
        ("green", "user / token"),
        ("purple", "auth"),
        ("amber", "resource"),
    ])
    d.save(str(G / "sequence.svg"))
    print("sequence", d.width, d.height)


def memory() -> None:
    d = Diagram(
        1020, 420,
        title="Agent memory architecture",
        desc="Input is processed by a memory manager that writes to a vector "
             "store and a graph store; retrieval and ranking assemble context "
             "for the model.",
    )
    inp = d.node(40, 168, "Input", "new message", family="green")
    mgr = d.node(220, 168, "Memory manager", "extract + route", family="purple")
    vec = d.cylinder(460, 70, "Vector store", "embeddings", family="green", w=180)
    graph = d.cylinder(460, 250, "Graph store", "relations", family="purple", w=180)
    rank = d.node(720, 168, "Retrieve + rank", "top-k + score")
    model = d.node(920, 168, "Model", "grounded prompt", family="amber")
    d.connect(inp, mgr, color="green", label="write")
    d.fanout(mgr, [vec, graph])
    # merge into rank without floating chevron: stem without marker + one arrow
    bus_x = rank.x - 28
    d.lpath([vec.right, (bus_x, vec.cy), (bus_x, rank.cy)], color="green")
    d.lpath([graph.right, (bus_x, graph.cy), (bus_x, rank.cy)], color="purple")
    d.arrow((bus_x, rank.cy), rank.left, label="read")
    d.connect(rank, model, color="amber", label="context")
    d.legend([
        ("green", "vector / write"),
        ("purple", "graph"),
        ("neutral", "retrieve"),
        ("amber", "model"),
    ])
    d.save(str(G / "memory-architecture.svg"))
    print("memory", d.width, d.height)


def er_diagram() -> None:
    d = Diagram(
        800, 420,
        title="E-commerce ER schema",
        desc="Users place orders; each order contains products.",
    )
    user = d.entity(40, 60, "User", ["id (PK)", "email", "name"], family="green", w=160)
    order = d.entity(320, 60, "Order", ["id (PK)", "user_id (FK)", "total"], w=160)
    product = d.entity(600, 60, "Product", ["id (PK)", "sku", "price"], w=160)
    places = d.diamond(220, 220, "places", family="amber", hh=36)
    contains = d.diamond(480, 220, "contains", family="amber", hh=36)
    d.connect(user, places, color="green")
    d.connect(places, order)
    d.connect(order, contains)
    d.connect(contains, product)
    # cardinality labels via raw
    d.raw(
        '<text x="175" y="170" dominant-baseline="central" font-size="12" '
        'fill="#3D3D3A">1</text>',
        layer="labels",
    )
    d.raw(
        '<text x="275" y="170" dominant-baseline="central" font-size="12" '
        'fill="#3D3D3A">N</text>',
        layer="labels",
    )
    d.raw(
        '<text x="420" y="170" dominant-baseline="central" font-size="12" '
        'fill="#3D3D3A">1</text>',
        layer="labels",
    )
    d.raw(
        '<text x="545" y="170" dominant-baseline="central" font-size="12" '
        'fill="#3D3D3A">N</text>',
        layer="labels",
    )
    d.legend([("green", "primary entity"), ("amber", "relationship")])
    d.save(str(G / "er-diagram.svg"))
    print("er", d.width, d.height)


def data_flow() -> None:
    d = Diagram(
        900, 250,
        title="Streaming data pipeline",
        desc="Events stream from Kafka through Spark into S3, then are queried "
             "by Athena. Each arrow is labeled with its data shape.",
    )
    kafka = d.node(40, 80, "Kafka", "event stream")
    spark = d.node(250, 80, "Spark", "transform", family="green")
    s3 = d.cylinder(460, 72, "S3", "parquet", family="green", w=150)
    athena = d.node(700, 80, "Athena", "SQL query", family="purple")
    d.connect(kafka, spark, label="stream")
    d.connect(spark, s3, color="green", label="batch")
    d.connect(s3, athena, color="purple", label="query")
    d.legend([
        ("green", "write path"),
        ("purple", "read path"),
        ("neutral", "ingest"),
    ])
    d.save(str(G / "data-flow.svg"))
    print("data-flow", d.width, d.height)


def data_flow_mobile() -> None:
    d = Diagram(
        360, 600,
        title="Streaming data pipeline (mobile)",
        desc="Vertical re-layout of the data-flow gallery diagram for narrow "
             "viewports.",
    )
    kafka = d.node(80, 40, "Kafka", "event stream", w=200)
    spark = d.node(80, 160, "Spark", "transform", family="green", w=200)
    s3 = d.cylinder(80, 280, "S3", "parquet", family="green", w=200)
    athena = d.node(80, 420, "Athena", "SQL query", family="purple", w=200)
    d.connect(kafka, spark, label="stream")
    d.connect(spark, s3, color="green", label="batch")
    d.connect(s3, athena, color="purple", label="query")
    d.legend([
        ("green", "write path"),
        ("purple", "read path"),
        ("neutral", "ingest"),
    ])
    d.save(str(G / "data-flow_mobile.svg"))
    print("data-flow_mobile", d.width, d.height)


def timeline() -> None:
    d = Diagram(
        760, 400,
        title="Product launch Gantt",
        desc="A four-phase project timeline — design, develop, test, launch — "
             "across six weeks, with two amber milestones marking the design "
             "freeze and the public release.",
    )
    d.heading("Product launch · 6 weeks")
    # row labels
    for i, name in enumerate(["Design", "Develop", "Test", "Launch"]):
        d.raw(
            f'<text x="40" y="{110 + i * 36}" dominant-baseline="central" '
            f'font-size="14" font-weight="500" fill="#141413">{name}</text>',
            layer="labels",
        )
    d.bar(100, 96, 140, "W1–W2", family="green")
    d.bar(180, 132, 260, "W2–W4", family="purple")
    d.bar(340, 168, 200, "W3–W5", family="amber")
    d.bar(480, 204, 140, "W5–W6", family="green")
    # milestones
    d.diamond(218, 250, "", family="amber", hw=22, hh=16)
    d.diamond(598, 250, "", family="amber", hw=22, hh=16)
    d.raw(
        '<text x="240" y="246" text-anchor="middle" dominant-baseline="central" '
        'font-size="12" fill="#633806">Design freeze</text>',
        layer="labels",
    )
    d.raw(
        '<text x="620" y="246" text-anchor="middle" dominant-baseline="central" '
        'font-size="12" fill="#633806">Public release</text>',
        layer="labels",
    )
    # axis
    d.raw(
        '<line x1="80" y1="320" x2="700" y2="320" stroke="#73726C" '
        'stroke-width="1.5" stroke-linecap="round"/>',
        layer="containers",
    )
    for i, lab in enumerate(["W1", "W2", "W3", "W4", "W5", "W6"]):
        x = 100 + i * 120
        d.raw(
            f'<line x1="{x}" y1="316" x2="{x}" y2="324" stroke="#73726C" '
            f'stroke-width="1.5"/>',
            layer="containers",
        )
        d.raw(
            f'<text x="{x}" y="338" text-anchor="middle" '
            f'dominant-baseline="central" font-size="12" fill="#3D3D3A">'
            f'{lab}</text>',
            layer="labels",
        )
    d.legend([
        ("green", "Design / Launch"),
        ("purple", "Develop"),
        ("amber", "Test / milestone"),
    ])
    d.save(str(G / "timeline-gantt.svg"))
    print("timeline", d.width, d.height)


def class_diagram() -> None:
    d = Diagram(
        760, 560,
        title="Animal class hierarchy",
        desc="An abstract Animal class with subclasses Dog and Cat, implementing "
             "the Comparable interface. UML relationships use the single "
             "open-chevron marker plus a label and line style.",
    )
    comp = d.class_box(
        300, 40, "Comparable",
        methods=["+compareTo(o): int"],
        family="green", stereotype="interface", w=160,
    )
    animal = d.class_box(
        300, 210, "Animal",
        attrs=["-name: String", "#age: int"],
        methods=["+eat(): void", "+sleep(): void"],
        abstract=True, w=160,
    )
    dog = d.class_box(
        120, 400, "Dog",
        attrs=["-trick: String"], methods=["+bark(): void"], w=160,
    )
    cat = d.class_box(
        480, 400, "Cat",
        attrs=["-indoor: bool"], methods=["+meow(): void"], w=160,
    )
    d.connect(animal, comp, dashed=True, label="implements")
    d.connect(dog, animal, label="extends")
    d.connect(cat, animal, label="extends")
    d.legend([
        ("green", "interface"),
        ("neutral", "abstract / concrete class"),
    ])
    d.save(str(G / "class-diagram.svg"))
    print("class", d.width, d.height)


def state_machine() -> None:
    d = Diagram(
        760, 400,
        title="Order fulfillment state machine",
        desc="An order moves from idle through processing; timeout routes to "
             "error, else done.",
    )
    d.state_dot(50, 80, "initial")
    idle = d.node(120, 52, "Idle", "awaiting payment")
    proc = d.node(340, 52, "Processing", "payment cleared", family="green")
    dec = d.diamond(500, 40, "timeout?", family="amber")
    done = d.node(400, 200, "Done", "shipped", family="green")
    err = d.node(580, 200, "Error", "payment timeout", family="terracotta")
    d.arrow((58, 80), idle.left, color="green", label="create")
    d.connect(idle, proc, color="green", label="pay")
    d.connect(proc, dec)
    d.lpath(
        [dec.bottom, (dec.cx, 150), (done.cx, 150), done.top],
        color="green", label="no",
    )
    d.lpath(
        [dec.bottom, (dec.cx, 150), (err.cx, 150), err.top],
        color="terracotta", label="yes",
    )
    d.arrow(done.bottom, (done.cx, 310), color="green", label="deliver")
    d.state_dot(done.cx, 322, "final")
    d.legend([("green", "happy path"), ("terracotta", "failure")])
    d.save(str(G / "state-machine.svg"))
    print("state", d.width, d.height)


def decision_ladder() -> None:
    d = Diagram(
        920, 400,
        title="Permission decision ladder",
        desc="A tool request walks a chain of numbered checks; each either "
             "allows (rises to Execute) or denies (drops to Blocked).",
    )
    d.bar(40, 44, 840, "Execute", family="green", h=28)
    d.bar(40, 300, 840, "Blocked", family="terracotta", h=28)
    steps = [
        d.step(88, 150, 1, "Hooks", "PreToolUse"),
        d.step(286, 150, 2, "Deny rules", "settings.json"),
        d.step(486, 150, 3, "Allow rules", "settings.json"),
        d.step(686, 150, 4, "canUseTool", "your code"),
    ]
    d.chain(steps)
    for s in steps:
        d.arrow(s.top, (s.cx, 72), color="green")
        d.arrow(s.bottom, (s.cx, 300), color="terracotta")
    d.legend([
        ("green", "allow → Execute"),
        ("terracotta", "deny → Blocked"),
    ])
    d.save(str(G / "decision-ladder.svg"))
    print("ladder", d.width, d.height)


def sample_comparison() -> None:
    d = Diagram(
        760, 380,
        title="RAG vs 微调 vs 提示工程",
        desc="三种为大模型注入知识的方法对比：RAG 检索外部知识、查询时拼接，知识可更新；"
             "微调改写模型权重，成本与延迟高；提示工程用少样本示例，受上下文窗口限制。",
    )
    d.heading("RAG vs 微调 vs 提示工程")
    rows = [
        [
            {"title": "RAG", "sub": "检索增强生成"},
            {"title": "检索外部知识", "sub": "查询时拼接"},
            {"title": "知识可更新", "sub": "无需重训", "family": "green"},
        ],
        [
            {"title": "微调", "sub": "Fine-tuning"},
            {"title": "改写模型权重", "sub": "需训练数据"},
            {"title": "成本与延迟高", "sub": "更新昂贵", "family": "terracotta"},
        ],
        [
            {"title": "提示工程", "sub": "Prompting"},
            {"title": "少样本示例", "sub": "写在提示里"},
            {"title": "受上下文窗口限制", "sub": "示例放不下", "family": "terracotta"},
        ],
    ]
    grid = d.grid(rows, x=40, y=64, gap_x=48, gap_y=40)
    for row in grid:
        d.chain(row)
    d.legend([("green", "优势"), ("terracotta", "局限")])
    d.save(str(S / "sample-comparison.svg"))
    print("sample-comparison", d.width, d.height)


def hero() -> None:
    d = Diagram(
        720, 540,
        title="RAG pipeline",
        desc="A user query is embedded, used to retrieve top-k chunks from a "
             "vector store, then passed with the retrieved context to an LLM "
             "that produces a grounded response. The vector store is populated "
             "offline by indexing a document corpus.",
    )
    d.heading("RAG pipeline")
    d.container(500, 56, 200, 252, label="Knowledge base")
    q = d.node(200, 64, "User query", "natural language", w=220)
    emb = d.node(200, 148, "Embed", "query → vector", w=220)
    ret = d.node(200, 232, "Retrieve", "top-k similar chunks", family="green", w=220)
    llm = d.node(200, 316, "LLM", "answer from context", w=220)
    resp = d.node(200, 400, "Response", "grounded answer", family="green", w=220)
    docs = d.node(520, 96, "Documents", "corpus", family="purple", w=160)
    store = d.node(520, 232, "Vector store", "embeddings", family="green", w=160)
    d.chain([q, emb, ret, llm, resp])
    d.connect(docs, store, color="purple", label="index")
    d.connect(store, ret, color="green")  # no redundant top-k edge label
    d.legend([
        ("green", "retrieval / answer"),
        ("purple", "index (write)"),
    ])
    d.save(str(S / "hero.svg"))
    print("hero", d.width, d.height)


def sample_agent_loop() -> None:
    d = Diagram(
        720, 360,
        title="Agent 工具调用循环",
        desc="用户提问后，LLM 进行推理并决定是否调用工具；工具执行后把观察结果回传给 LLM，"
             "形成循环；当 LLM 判断信息充分时，输出最终答案。",
    )
    d.heading("Agent 工具调用循环")
    user = d.node(260, 44, "用户提问", "自然语言", w=200)
    llm = d.node(260, 140, "LLM", "推理并决定", w=200)
    call = d.node(260, 240, "工具调用", "选择并发起", w=200)
    tool = d.node(520, 240, "工具", "搜索 · 代码 · 计算", family="amber", w=160)
    done = d.node(40, 140, "最终答案", "信息充分时输出", family="green", w=160)
    d.connect(user, llm)
    d.connect(llm, call, label="调用")
    d.connect(call, tool, color="amber")
    d.lpath(
        [tool.top, (tool.cx, 168), (llm.x + llm.w, 168), llm.right],
        color="purple", label="观察",
    )
    d.connect(llm, done, color="green", label="完成")
    d.legend([
        ("green", "完成路径"),
        ("amber", "工具"),
        ("purple", "循环 / 反馈"),
    ])
    d.save(str(S / "sample-agent-loop.svg"))
    print("sample-agent-loop", d.width, d.height)


def main() -> None:
    mind_map()
    architecture()
    flowchart()
    comparison()
    network()
    sequence()
    memory()
    er_diagram()
    data_flow()
    data_flow_mobile()
    timeline()
    class_diagram()
    state_machine()
    decision_ladder()
    sample_comparison()
    hero()
    sample_agent_loop()
    print("ALL DONE")


if __name__ == "__main__":
    main()
