"""Decision, lifecycle, and concept-map reference layouts."""

from .common import canvas, footer


def flowchart():
    d = canvas(640, 608, "Pull request workflow",
               "Open a pull request, review the change and run tests, then merge after the required checks pass. Failed checks return through a fixes branch.",
               "Review, validate, and merge")
    opened = d.node(128, 96, "Open PR", "diff ready", w=192)
    review = d.node(128, 208, "Review + tests", "required checks", w=192)
    decision = d.diamond(128, 320, "Checks pass?", hw=96, hh=44)
    merged = d.node(128, 464, "Merge", "accept reviewed diff", family="green", w=192)
    fixes = d.node(424, 336, "Fix issues", "amend diff", family="terracotta", w=176)
    d.arrow(opened.bottom, review.top)
    d.arrow(review.bottom, decision.top)
    d.arrow(decision.bottom, merged.top, color="green", label="yes", label_offset=12)
    d.arrow(decision.right, fixes.left, color="terracotta", label="no", label_offset=12)
    d.lpath([fixes.top, (fixes.cx, review.cy), review.right], color="terracotta", label="review again", label_offset=12)
    footer(d, [("neutral", "Review"), ("amber", "Decision"), ("green", "Passed"), ("terracotta", "Rework")])
    return d


def decision_ladder():
    d = canvas(920, 440, "Ordered policy checks",
               "Three illustrative policy groups are evaluated in order. A matching allow or deny exits the chain; no match continues. If no group matches, the explicit default is deny.",
               "A final verdict exits; no match continues to the next group")
    d.node(40, 96, "Allow", family="green", w=840, h=32)
    d.node(40, 320, "Deny", family="terracotta", w=840, h=32)
    steps = [d.step(x, 196, i, title, sub, w=160)
             for i, (x, title, sub) in enumerate([
                 (56, "Group A", "first check"), (272, "Group B", "second check"),
                 (488, "Group C", "last check"),
             ], 1)]
    for step in steps:
        d.arrow(step.top, (step.cx, 128), color="green", label="allow", label_offset=12)
        d.arrow(step.bottom, (step.cx, 320), color="terracotta", label="deny", label_offset=12)
    for first, second in zip(steps, steps[1:]):
        d.arrow(first.right, second.left, label="next", label_offset=12)
    fallback = d.node(704, 196, "Default", "no group matched", family="terracotta", w=160)
    d.arrow(steps[-1].right, fallback.left, label="next", label_offset=12)
    d.arrow(fallback.bottom, (fallback.cx, 320), color="terracotta", label="deny", label_offset=12)
    footer(d, [("neutral", "Continue"), ("green", "Allow"), ("terracotta", "Deny")])
    return d


def state_machine():
    d = canvas(720, 632, "Job lifecycle",
               "A submitted job is queued and then started. Completion branches on the result: success can be archived, while a failed job can be retried.",
               "Events and guards determine each transition")
    d.state_dot(80, 124)
    idle = d.state(144, 96, "Queued", "awaiting a worker", w=168)
    processing = d.state(424, 96, "Running", "executing the job", w=216)
    choice = d.diamond(444, 220, "Succeeded?", hw=88, hh=44)
    done = d.state(156, 380, "Succeeded", "output ready", family="green", w=168)
    error = d.state(448, 380, "Failed", "error recorded", family="terracotta", w=168)
    d.state_dot(done.cx, 532, kind="final")
    d.arrow((88, 124), idle.left, label="submit", label_offset=12)
    d.arrow(idle.right, processing.left, label="start / run", label_offset=12)
    d.arrow(processing.bottom, choice.top, label="complete", label_offset=12)
    d.lpath([choice.left, (done.cx, choice.cy), done.top], color="green", label="[yes]", label_offset=12)
    d.arrow(choice.bottom, error.top, color="terracotta", label="[no]", label_offset=12)
    d.lpath([error.right, (680, error.cy), (680, processing.cy), processing.right],
            color="terracotta", label="retry", label_offset=-12)
    d.arrow(done.bottom, (done.cx, 520), color="green", label="archive", label_offset=12)
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
