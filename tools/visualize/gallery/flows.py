"""Decision, lifecycle, and concept-map reference layouts."""

from .common import canvas, footer


def flowchart():
    d = canvas(640, 608, "Pull request workflow",
               "Open a pull request, review it, and deploy after tests pass. Failed checks return through a fixes branch.",
               "Review, validate, and deploy")
    opened = d.node(128, 96, "Open PR", "diff ready", w=192)
    review = d.node(128, 208, "Code review", "human + lint", w=192)
    decision = d.diamond(128, 320, "Tests pass?", hw=96, hh=44)
    deploy = d.node(128, 464, "Deploy", "ship to production", family="green", w=192)
    fixes = d.node(424, 336, "Fix issues", "amend diff", family="terracotta", w=176)
    d.arrow(opened.bottom, review.top)
    d.arrow(review.bottom, decision.top)
    d.arrow(decision.bottom, deploy.top, color="green", label="yes", label_offset=12)
    d.arrow(decision.right, fixes.left, color="terracotta", label="no", label_offset=12)
    d.lpath([fixes.top, (fixes.cx, review.cy), review.right], color="terracotta", label="review again", label_offset=12)
    footer(d, [("neutral", "Review"), ("amber", "Decision"), ("green", "Passed"), ("terracotta", "Rework")])
    return d


def decision_ladder():
    d = canvas(920, 440, "Tool permission decisions",
               "Ordered checks may allow, deny, or continue to the next check. The rails show final verdicts.",
               "A final verdict exits the chain; otherwise continue to the next check")
    d.node(40, 96, "Execute", family="green", w=840, h=32)
    d.node(40, 320, "Blocked", family="terracotta", w=840, h=32)
    steps = [d.step(x, 196, i, title, sub, w=160)
             for i, (x, title, sub) in enumerate([
                 (56, "Hooks", "tool event"), (272, "Deny rules", "policy match"),
                 (488, "Allow rules", "policy match"), (704, "canUseTool", "custom check"),
             ], 1)]
    for step in steps:
        d.arrow(step.top, (step.cx, 128), color="green", label="allow", label_offset=12)
        d.arrow(step.bottom, (step.cx, 320), color="terracotta", label="deny", label_offset=12)
    for first, second in zip(steps, steps[1:]):
        d.arrow(first.right, second.left, label="next", label_offset=12)
    footer(d, [("neutral", "Continue"), ("green", "Allow"), ("terracotta", "Deny")])
    return d


def state_machine():
    d = canvas(720, 632, "Order lifecycle",
               "Create an order, pay and confirm it, then ship on success or enter the timeout error state.",
               "Events and guards determine each transition")
    d.state_dot(80, 124)
    idle = d.state(144, 96, "Idle", "awaiting payment", w=168)
    processing = d.state(424, 96, "Processing", "payment cleared", family="green", w=216)
    choice = d.diamond(444, 220, "Timeout?", hw=88, hh=44)
    done = d.state(156, 380, "Done", "shipped", family="green", w=168)
    error = d.state(448, 380, "Error", "payment timeout", family="terracotta", w=168)
    d.state_dot(done.cx, 532, kind="final")
    d.arrow((88, 124), idle.left, label="create", label_offset=12)
    d.arrow(idle.right, processing.left, color="green", label="pay / confirm", label_offset=12)
    d.arrow(processing.bottom, choice.top)
    d.lpath([choice.left, (done.cx, choice.cy), done.top], color="green", label="[no]", label_offset=12)
    d.arrow(choice.bottom, error.top, color="terracotta", label="[yes]", label_offset=12)
    d.arrow(done.bottom, (done.cx, 520), color="green", label="deliver", label_offset=12)
    footer(d, [("neutral", "Lifecycle"), ("green", "Success"), ("amber", "Choice"), ("terracotta", "Failure")])
    return d


def mind_map():
    d = canvas(760, 520, "AI agent capabilities",
               "Perception, learning, memory, action, and reasoning branch from one core agent loop.",
               "Five capabilities organized around one core loop")
    center = d.node(280, 260, "AI agent", "core loop", w=200)
    leaves = [
        d.node(300, 108, "Perception", family="green", w=160),
        d.node(40, 204, "Learning", "adapt from feedback", family="green", w=160),
        d.node(40, 364, "Action", "interact with tools", family="green", w=160),
        d.node(560, 204, "Memory", "recall prior context", family="green", w=160),
        d.node(560, 364, "Reasoning", "plan the next step", family="green", w=160),
    ]
    for leaf in leaves:
        d.branch(center, leaf, family="green")
    footer(d, [("neutral", "Core loop"), ("green", "Capabilities")])
    return d
