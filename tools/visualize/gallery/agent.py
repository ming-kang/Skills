"""The intentionally wide, information-dense agent-loop reference."""

from svgkit import FAMILIES

from .common import canvas, footer, rail, text


def agent_loop():
    d = canvas(1360, 924, "Agent loop · turn 7 of N",
               "Intake builds context, the model selects tools, and outputs are verified. Failed verification loops back; successful results become the response. Memory is a separate read/write rail.",
               "Intake, tool use, verification, and persisted memory")
    for index in range(11):
        fill = FAMILIES["green"]["line"] if index < 7 else FAMILIES["neutral"]["fill"]
        d.raw(f'<rect x="{760 + index * 22}" y="25" width="16" height="14" '
              f'rx="3" fill="{fill}"/>')
    text(d, 760, 56, "Each filled cell is a completed turn")
    d.container(40, 96, 232, 420, "1 · Intake", "inputs to this turn")
    d.container(328, 96, 248, 420, "2 · Reasoning", "prepare and choose")
    d.container(632, 96, 300, 500, "3 · Tools", "one selected action")
    d.container(988, 96, 332, 420, "Memory", "read + write")
    d.container(40, 652, 1280, 184, "4 · Verify and finalize", "accept or continue")

    request = d.node(60, 164, "User request", "task + limits", family="green", w=192)
    history = d.node(60, 272, "Session history", "prior 6 turns", w=192)
    snapshot = d.node(60, 380, "Repo snapshot", "tree + diffs", w=192)
    context = d.node(356, 164, "Context builder", "assemble prompt", family="green", w=192)
    model = d.node(356, 276, "Model", "reason + plan step", family="purple", w=192)
    router = d.node(356, 388, "Tool router", "choose one action", family="purple", w=192)
    for item in (request, history, snapshot):
        rail(d, [item.right, (300, item.cy)])
    rail(d, [(300, request.cy), (300, snapshot.cy)])
    d.arrow((300, context.cy), context.left, color="green")
    d.arrow(context.bottom, model.top, color="green", label="prompt", label_offset=12)
    d.arrow(model.bottom, router.top, color="purple", label="action", label_offset=12)

    tools = [d.node(660, y, title, sub, family=family, w=192)
             for y, title, sub, family in [
                 (164, "Read file", "file contents", "neutral"),
                 (244, "Apply edit", "write patch", "amber"),
                 (324, "Run shell", "command output", "amber"),
                 (404, "Search", "text + symbols", "neutral"),
                 (484, "Run tests", "verification", "green"),
             ]]
    rail(d, [router.right, (608, router.cy)], "purple")
    rail(d, [(608, tools[0].cy), (608, tools[-1].cy)], "purple")
    for tool in tools:
        d.arrow((608, tool.cy), tool.left, color=tool.family)
        rail(d, [tool.right, (908, tool.cy)])
    rail(d, [(908, tools[0].cy), (908, 628), (1152, 628)])

    working = d.node(1020, 164, "Working", "current goal", family="green", w=264)
    episodic = d.node(1020, 276, "Episodic", "past actions", w=264)
    semantic = d.node(1020, 388, "Semantic", "code knowledge", w=264)
    d.lpath([model.right, (592, model.cy), (592, 76), (964, 76),
             (964, working.cy), working.left], color="green", dashed=True, both=True)
    rail(d, [(964, working.cy), (964, semantic.cy)], "green", dashed=True)
    for memory in (episodic, semantic):
        d.arrow((964, memory.cy), memory.left, color="green", dashed=True)

    response = d.node(60, 732, "Response", "answer + diff", family="green", w=192)
    patch = d.node(356, 732, "Patch set", "verified changes", family="green", w=192)
    verifier = d.node(660, 732, "Verifier", "diff + tests", family="amber", w=192)
    observation = d.node(1020, 732, "Observation", "tool output", family="amber", w=264)
    d.arrow((1152, 628), observation.top, label="observe", label_offset=12)
    d.arrow(observation.left, verifier.right, color="amber", label="result", label_offset=12)
    d.arrow(verifier.left, patch.right, color="green", label="pass", label_offset=12)
    d.arrow(patch.left, response.right, color="green")
    d.lpath([verifier.top, (verifier.cx, 616), (312, 616), (312, model.cy), model.left],
            color="terracotta", label="retry", label_offset=12)
    footer(d, [("neutral", "Inputs / read"), ("green", "Context / success"), ("purple", "Reasoning"),
               ("amber", "Tool / mutation"), ("terracotta", "Retry")],
           [("green", "Memory read / write", True)])
    return d
