"""Documentation showcases, including Chinese typography examples."""

from .common import canvas, footer, text


def hero():
    d = canvas(760, 704, "RAG pipeline",
               "A query is embedded, retrieves top-k chunks from an offline-indexed vector store, and reaches an LLM that returns a grounded answer.",
               "Online retrieval backed by an offline document index")
    text(d, 80, 88, "Query time", size=14)
    d.container(452, 104, 268, 320, "Knowledge base", "offline indexing")
    query = d.node(80, 112, "User query", "natural language", w=224)
    embed = d.node(80, 224, "Embed", "query → vector", w=224)
    retrieve = d.node(80, 336, "Retrieve", "top-k similar chunks", family="green", w=224)
    llm = d.node(80, 448, "LLM", "answer from context", w=224)
    response = d.node(80, 560, "Response", "grounded answer", family="green", w=224)
    documents = d.node(496, 168, "Documents", "corpus", family="purple", w=180)
    store = d.cylinder(496, 328, "Vector store", "embeddings", w=180)
    for source, target, family, label in [
        (query, embed, "neutral", None), (embed, retrieve, "green", "vector"),
        (retrieve, llm, "green", "context"), (llm, response, "green", "answer"),
    ]:
        d.arrow(source.bottom, target.top, color=family, label=label, label_offset=12)
    d.arrow(documents.bottom, store.top, color="purple", label="index", label_offset=12)
    d.arrow(store.left, retrieve.right, color="green", label="top-k", label_offset=12)
    footer(d, [("neutral", "Query / generation"), ("green", "Retrieval / answer"), ("purple", "Indexing")])
    return d


def sample_agent_loop():
    d = canvas(760, 488, "Agent 工具调用循环",
               "用户提问后，LLM 决定输出答案或调用工具；工具结果返回 LLM，形成反馈循环。",
               "依据工具结果继续推理，信息充分时输出答案")
    query = d.node(280, 104, "用户提问", "自然语言", w=200)
    llm = d.node(280, 216, "LLM", "推理并决定", w=200)
    call = d.node(280, 328, "工具调用", "选择并发起", w=200)
    answer = d.node(40, 216, "最终答案", "信息充分时输出", family="green", w=168)
    tools = d.node(568, 328, "工具", "搜索 · 代码 · 计算", family="amber", w=152)
    d.arrow(query.bottom, llm.top)
    d.arrow(llm.bottom, call.top, label="调用", label_offset=12)
    d.arrow(llm.left, answer.right, color="green", label="完成", label_offset=12)
    d.arrow(call.right, tools.left, color="amber", label="执行", label_offset=12)
    d.lpath([tools.top, (tools.cx, llm.cy), llm.right], color="purple", label="反馈", label_offset=12)
    footer(d, [("neutral", "推理"), ("green", "完成"), ("amber", "工具"), ("purple", "反馈")])
    return d


def sample_comparison():
    d = canvas(800, 452, "RAG、微调与提示工程",
               "比较三种方法的实现方式与主要取舍：RAG 检索知识，微调更新权重，提示工程组织指令与示例。",
               "实现方式与主要取舍")
    for x, label in [(124, "方法"), (392, "实现方式"), (672, "特点")]:
        text(d, x, 98, label, size=14, anchor="middle")
    rows = [
        ("RAG", "检索增强生成", "检索外部知识", "查询时拼接", "知识可更新", "无需重新训练", "green"),
        ("微调", "Fine-tuning", "更新模型权重", "使用训练数据", "更新需要重训", "增加训练与维护成本", "terracotta"),
        ("提示工程", "Prompting", "加入指令与示例", "直接组织上下文", "受上下文长度限制", "需控制提示与示例", "terracotta"),
    ]
    for index, (name, sub, mechanism, detail, verdict, note, family) in enumerate(rows):
        y = 136 + index * 84
        method = d.node(40, y, name, sub, w=168)
        process = d.node(288, y, mechanism, detail, w=208)
        outcome = d.node(584, y, verdict, note, family=family, w=176)
        d.arrow(method.right, process.left)
        d.arrow(process.right, outcome.left)
    footer(d, [("neutral", "方法与机制"), ("green", "优势"), ("terracotta", "局限")])
    return d


def svgkit_rag():
    d = canvas(840, 272, "RAG pipeline",
               "A Chinese query is embedded, used to retrieve passages, and passed to a language model for a grounded answer.",
               "From a question to an answer grounded in retrieved passages")
    query = d.node(40, 120, "查询", "用户问题", w=136)
    embed = d.node(244, 120, "Embed", "to vector", w=136)
    retrieve = d.node(448, 120, "Retriever", "top-k passages", family="green", w=144)
    llm = d.node(660, 120, "LLM", "grounded answer", family="purple", w=140)
    d.arrow(query.right, embed.left)
    d.arrow(embed.right, retrieve.left, color="green", label="vector", label_offset=12)
    d.arrow(retrieve.right, llm.left, color="purple", label="context", label_offset=12)
    footer(d, [("neutral", "Query / embedding"), ("green", "Retrieval"), ("purple", "Generation")])
    return d
