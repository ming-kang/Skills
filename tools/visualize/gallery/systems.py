"""Architecture, pipeline, memory, and network reference layouts."""

from .common import canvas, footer, rail


def architecture():
    d = canvas(760, 640, "Microservice architecture",
               "A gateway routes to three services; users and orders share PostgreSQL, while billing uses Redis.",
               "Request routing and shared persistence")
    client = d.node(292, 96, "Client", "web + mobile", w=176)
    gateway = d.node(292, 208, "API gateway", "routing + auth", w=176)
    d.container(40, 288, 680, 136, "Services")
    users = d.node(64, 340, "User service", "accounts", w=176)
    orders = d.node(292, 340, "Order service", "checkout", w=176)
    payments = d.node(520, 340, "Payment service", "billing", family="amber", w=176)
    database = d.cylinder(162, 480, "PostgreSQL", "orders + users", w=208, h=48)
    cache = d.cylinder(504, 480, "Redis", "session cache", w=208, h=48)
    d.arrow(client.bottom, gateway.top, label="HTTPS", label_offset=12)
    rail(d, [gateway.bottom, (380, 316)])
    rail(d, [(users.cx, 316), (payments.cx, 316)])
    for service in (users, orders, payments):
        d.arrow((service.cx, 316), service.top)
    for service in (users, orders):
        rail(d, [service.bottom, (service.cx, 448)], "green")
    rail(d, [(users.cx, 448), (orders.cx, 448)], "green")
    d.arrow((database.cx, 448), database.top, color="green")
    d.arrow(payments.bottom, cache.top, color="green", label="cache", label_offset=12)
    footer(d, [("neutral", "Application"), ("green", "Persistence"), ("amber", "Billing")])
    return d


def data_flow():
    d = canvas(760, 272, "Streaming data pipeline",
               "Kafka streams events to Spark, which writes Parquet to S3 for Athena queries.",
               "Ingest events, transform batches, then query the stored data")
    kafka = d.node(40, 120, "Kafka", "event stream", w=128)
    spark = d.node(224, 120, "Spark", "transform", family="green", w=128)
    store = d.cylinder(408, 112, "S3", "Parquet", w=128)
    athena = d.node(592, 120, "Athena", "SQL query", family="purple", w=128)
    for source, target, family, label in (
        (kafka, spark, "neutral", "stream"),
        (spark, store, "green", "batch"),
        (store, athena, "purple", "files"),
    ):
        d.arrow(source.right, target.left, color=family, label=label, label_offset=12)
    footer(d, [("neutral", "Ingest"), ("green", "Write path"), ("purple", "Read path")])
    return d


def data_flow_mobile():
    d = canvas(360, 608, "Streaming data pipeline",
               "The same Kafka, Spark, S3, and Athena pipeline arranged vertically for a narrow viewport.",
               "The same flow, arranged vertically")
    kafka = d.node(80, 104, "Kafka", "event stream", w=200)
    spark = d.node(80, 220, "Spark", "transform", family="green", w=200)
    store = d.cylinder(80, 336, "S3", "Parquet", w=200)
    athena = d.node(80, 464, "Athena", "SQL query", family="purple", w=200)
    for source, target, family, label in (
        (kafka, spark, "neutral", "stream"),
        (spark, store, "green", "batch"),
        (store, athena, "purple", "files"),
    ):
        d.arrow(source.bottom, target.top, color=family, label=label, label_offset=12)
    footer(d, [("neutral", "Ingest"), ("green", "Write path"), ("purple", "Read path")])
    return d


def memory_architecture():
    d = canvas(1000, 528, "Memory read and write paths",
               "The manager writes extracted memories to vector and graph stores. A separate query drives retrieval and ranking of both stores into context.",
               "Persist new information, then retrieve context for the next turn")
    incoming = d.node(40, 228, "Input", "new message", w=136)
    manager = d.node(240, 228, "Memory manager", "extract + route", family="purple", w=192)
    vector = d.cylinder(512, 112, "Vector store", "embeddings", family="neutral", w=184)
    graph = d.cylinder(512, 328, "Graph store", "relations", family="neutral", w=184)
    query = d.node(800, 96, "Query", "current question", w=160)
    retrieve = d.node(800, 228, "Retrieve + rank", "top-k + score", family="green", w=160)
    context = d.node(800, 384, "Context", "for the next turn", family="green", w=160)
    d.arrow(incoming.right, manager.left, color="purple", label="write", label_offset=12)
    rail(d, [manager.right, (472, manager.cy)], "purple")
    rail(d, [(472, vector.cy), (472, graph.cy)], "purple")
    for store in (vector, graph):
        d.arrow((472, store.cy), store.left, color="purple")
        rail(d, [store.right, (752, store.cy)], "green")
    rail(d, [(752, vector.cy), (752, graph.cy)], "green")
    d.arrow((752, retrieve.cy), retrieve.left, color="green")
    d.arrow(query.bottom, retrieve.top, color="green", label="lookup", label_offset=12)
    d.arrow(retrieve.bottom, context.top, color="green", label="top-k", label_offset=12)
    footer(d, [("neutral", "Input / storage"), ("purple", "Write path"), ("green", "Read path")])
    return d


def network_topology():
    d = canvas(720, 664, "Network topology",
               "HTTPS traffic crosses the firewall into a DMZ subnet and is routed to two application hosts.",
               "A filtered ingress path into the application subnet")
    internet = d.node(270, 96, "Internet", "public WAN", w=180)
    firewall = d.node(270, 208, "Firewall", "ingress filter", family="terracotta", w=180)
    d.container(40, 304, 640, 264, "DMZ", "10.0.1.0/24")
    switch = d.node(270, 364, "Core switch", "L3 routing", w=180)
    hosts = [d.node(x, 476, f"App server {name}", ip, family="green", w=180)
             for x, name, ip in [(108, "A", "10.0.1.10"), (432, "B", "10.0.1.11")]]
    d.arrow(internet.bottom, firewall.top, label="HTTPS", label_offset=12)
    d.arrow(firewall.bottom, switch.top, label="filtered", label_offset=12)
    rail(d, [switch.bottom, (switch.cx, 450)], "green")
    rail(d, [(hosts[0].cx, 450), (hosts[1].cx, 450)], "green")
    for host in hosts:
        d.arrow((host.cx, 450), host.top, color="green")
    footer(d, [("neutral", "Network"), ("terracotta", "Security boundary"), ("green", "Application hosts")])
    return d
