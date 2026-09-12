"""Sequence, class, use-case, and entity relationship examples."""

from .common import activation, canvas, footer, rail, text


def sequence():
    d = canvas(760, 536, "Authorization code flow",
               "The browser authorizes with the auth server, redirects a code to the client, and the client exchanges it for a token.",
               "Browser redirects, then the client exchanges the code")
    browser = d.lifeline(60, "Browser", 96, 440, w=160)
    client = d.lifeline(300, "Client", 96, 440, w=160)
    auth = d.lifeline(540, "Auth server", 96, 440, family="purple", w=160)
    for source, target, y, label, family, dashed in [
        (browser, auth, 192, "authorize request", "purple", False),
        (auth, browser, 248, "login + consent", "neutral", True),
        (browser, client, 304, "auth code", "green", False),
        (client, auth, 360, "exchange code", "purple", False),
        (auth, client, 416, "access token", "green", True),
    ]:
        d.arrow((source.x, y), (target.x, y), label=label, color=family,
                dashed=dashed, plate=True, label_offset=12)
    footer(d, [("purple", "Auth request"), ("green", "Credentials")],
           [("neutral", "Request", False), ("neutral", "Return", True)])
    return d


def sequence_frames():
    d = canvas(800, 644, "Authentication fragments",
               "A login request receives a token or rejection in an alt fragment. An opt fragment calls the API only with permission.",
               "Alternative outcomes and an optional API call")
    client = d.lifeline(168, "Client", 96, 548, w=144)
    auth = d.lifeline(388, "Auth service", 96, 548, family="purple", w=144)
    api = d.lifeline(608, "API", 96, 548, family="green", w=144)
    activation(d, client.x, 164, 516)
    activation(d, auth.x, 172, 340, "purple")
    activation(d, api.x, 440, 516, "green")
    d.scope(40, 212, 720, 152, "alt")
    d.raw('<line x1="40" y1="284" x2="760" y2="284" '
          'stroke="rgba(31,30,29,0.3)" stroke-width="0.5" stroke-dasharray="4 3"/>', layer="containers")
    text(d, 62, 260, "[valid]", role="container-label")
    text(d, 62, 320, "[invalid]", role="container-label")
    d.scope(40, 400, 720, 132, "opt", "has permission")
    for source_x, target_x, y, label, family, dashed in [
        (client.x + 6, auth.x - 6, 172, "login", "purple", False),
        (auth.x - 6, client.x + 6, 256, "token", "purple", True),
        (auth.x - 6, client.x + 6, 328, "denied", "terracotta", True),
        (client.x + 6, api.x - 6, 448, "request", "green", False),
        (api.x - 6, client.x + 6, 500, "response", "green", True),
    ]:
        d.arrow((source_x, y), (target_x, y), label=label, color=family,
                dashed=dashed, plate=True, label_offset=12)
    footer(d, [("purple", "Authentication"), ("green", "Authorized call"), ("terracotta", "Rejected")],
           [("neutral", "Request", False), ("neutral", "Return", True)])
    return d


def class_diagram():
    d = canvas(680, 636, "Class hierarchy",
               "Animal implements Comparable. Dog and Cat extend the abstract Animal class. Compartments show names, attributes, and methods.",
               "An interface, an abstract base class, and two concrete classes")
    interface = d.class_box(236, 96, "Comparable", methods=["+compareTo(o): int"],
                            family="green", stereotype="interface", w=208)
    animal = d.class_box(236, 264, "Animal", ["-name: String", "#age: int"],
                        ["+eat(): void", "+sleep(): void"], abstract=True, w=208)
    dog = d.class_box(72, 464, "Dog", ["-trick: String"], ["+bark(): void"], w=208)
    cat = d.class_box(400, 464, "Cat", ["-indoor: bool"], ["+meow(): void"], w=208)
    d.arrow(animal.top, interface.bottom, dashed=True, label="«implements»", label_offset=12)
    rail(d, [dog.top, (dog.cx, 424), (cat.cx, 424), cat.top])
    d.arrow((animal.cx, 424), animal.bottom)
    text(d, animal.cx + 12, 403, "extends", role="arrow-label")
    footer(d, [("green", "Interface"), ("neutral", "Class")],
           [("neutral", "Inheritance", False), ("neutral", "Implementation", True)])
    return d


def er_diagram():
    d = canvas(760, 440, "Order data model",
               "One user places many orders. Orders and products have a many-to-many conceptual relationship; PK and FK mark keys.",
               "Conceptual relationships; PK and FK identify keys")
    user = d.entity(40, 96, "User", ["id (PK)", "email", "name"], family="green", w=176)
    order = d.entity(292, 96, "Order", ["id (PK)", "user_id (FK)", "total"], w=176)
    product = d.entity(544, 96, "Product", ["id (PK)", "sku", "price"], w=176)
    places = d.diamond(192, 260, "places", hw=60, hh=38)
    contains = d.diamond(448, 260, "contains", hw=68, hh=38)
    d.lpath([user.bottom, (user.cx, places.cy), places.left], color="green")
    d.lpath([places.right, (350, places.cy), (350, order.bottom[1])])
    d.lpath([(410, order.bottom[1]), (410, contains.cy), contains.left])
    d.lpath([contains.right, (product.cx, contains.cy), product.bottom])
    for x, cardinality in [(140, "1"), (362, "N"), (422, "M"), (644, "N")]:
        text(d, x, 218, cardinality, role="arrow-label")
    footer(d, [("green", "Customer"), ("neutral", "Entity"), ("amber", "Relationship")])
    return d


def use_case():
    d = canvas(900, 636, "Store use cases",
               "Customers browse and order. Orders include payment. Administrators manage inventory and apply an optional discount that extends ordering.",
               "Actors stay outside the system; relationships stay inside")
    d.container(160, 96, 580, 420, "E-commerce system", "online store")
    customer = d.actor(80, 268, "Customer")
    admin = d.actor(820, 268, "Admin")
    browse = d.usecase(196, 176, "Browse products", w=184)
    order = d.usecase(196, 300, "Place order", family="green", w=184)
    inventory = d.usecase(512, 176, "Manage inventory", w=184)
    payment = d.usecase(512, 300, "Process payment", w=184)
    discount = d.usecase(512, 420, "Apply discount", family="amber", w=184)
    rail(d, [customer.right, (128, customer.cy)])
    rail(d, [(128, browse.cy), (128, order.cy)])
    for usecase in (browse, order):
        d.arrow((128, usecase.cy), usecase.left)
    rail(d, [admin.left, (772, admin.cy)])
    rail(d, [(772, inventory.cy), (772, discount.cy)])
    for usecase in (inventory, discount):
        d.arrow((772, usecase.cy), usecase.right)
    d.arrow(order.right, payment.left, dashed=True, label="«include»", label_offset=12)
    d.lpath([discount.top, (discount.cx, 392), (order.cx, 392), order.bottom],
            dashed=True, label="«extend»", label_offset=12)
    footer(d, [("neutral", "Actor / use case"), ("green", "Primary use case"), ("amber", "Extension")],
           [("neutral", "Association", False), ("neutral", "Include / extend", True)])
    return d
