# Product Colors — brand lookup (optional)

> **House style first.** Default nodes are flat rounded rects with **color family** fills (`references/shape-vocabulary.md`). Use the tables below **only when the user names a specific product** and a brand-colored badge helps recognition. Prefer `svgkit.node()` / `svgkit.cylinder()` over ornamented badges.

> **Reference table, not a paste target.** The brand colors below are mostly cold (blue-dominant) and will trip `validate_svg.py`'s warm-palette check if pasted verbatim into a diagram. Use at most **1-2 product badges per figure** as intentional accents; keep everything else in the warm family palette from `references/style.md`.

## Product Icons (Brand Colors + Inline SVG)

All use circle badge + text abbreviation pattern. Replace `cx`, `cy` with actual coordinates.

### AI / ML Products

| Product | Color | Badge Text |
|---------|-------|-----------|
| OpenAI / ChatGPT | `#10A37F` | `OAI` |
| Anthropic / Claude | `#D97757` | `Claude` |
| Google Gemini | `#4285F4` | `Gemini` |
| Meta LLaMA | `#0467DF` | `LLaMA` |
| Mistral | `#FF7000` | `Mistral` |
| Cohere | `#39594D` | `Cohere` |
| Groq | `#F55036` | `Groq` |
| Together AI | `#6366F1` | `Together` |
| Replicate | `#191919` | `Rep` |
| Hugging Face | `#FFD21E` (text dark) | `HF` |

**Template:**
```xml
<circle cx="cx" cy="cy" r="22" fill="BRAND_COLOR"/>
<text x="cx" y="cy+5" text-anchor="middle" fill="white"
      font-size="10" font-weight="700" font-family="Helvetica">BADGE_TEXT</text>
<!-- Optional: outer ring for "AI" products -->
<circle cx="cx" cy="cy" r="24" fill="none" stroke="BRAND_COLOR" stroke-width="1" opacity="0.4"/>
```

### AI Memory & RAG Products

| Product | Color | Badge |
|---------|-------|-------|
| Mem0 | `#6366F1` | `mem0` |
| LangChain | `#1C3C3C` | `🦜` or `LC` |
| LlamaIndex | `#8B5CF6` | `LI` |
| LangGraph | `#1C3C3C` | `LG` |
| CrewAI | `#EF4444` | `Crew` |
| AutoGen | `#0078D4` | `AG` |
| Haystack | `#FF6D00` | `🌾` or `HS` |
| DSPy | `#7C3AED` | `DSPy` |

### Vector Databases

| Product | Color | Badge |
|---------|-------|-------|
| Pinecone | `#1C1C2E` + green | `Pine` |
| Weaviate | `#FA0050` | `Wea` |
| Qdrant | `#DC244C` | `Qdrant` |
| Chroma | `#FF6B35` | `Chr` |
| Milvus | `#00A1EA` | `Milvus` |
| pgvector | `#336791` | `pgv` |
| Faiss | `#0467DF` | `FAISS` |

**Vector DB template (cylinder + badge):**
```xml
<!-- Cylinder shape -->
<ellipse cx="cx" cy="top" rx="40" ry="12" fill="FILL" stroke="STROKE" stroke-width="1.5"/>
<rect x="cx-40" y="top" width="80" height="50" fill="FILL" stroke="none"/>
<line x1="cx-40" y1="top" x2="cx-40" y2="top+50" stroke="STROKE" stroke-width="1.5"/>
<line x1="cx+40" y1="top" x2="cx+40" y2="top+50" stroke="STROKE" stroke-width="1.5"/>
<ellipse cx="cx" cy="top+50" rx="40" ry="12" fill="FILL_DARK" stroke="STROKE" stroke-width="1.5"/>
<!-- Product name -->
<text x="cx" y="top+30" text-anchor="middle" fill="white"
      font-size="11" font-weight="700">Pinecone</text>
```

### Classic Databases & Storage

| Product | Color |
|---------|-------|
| PostgreSQL | `#336791` |
| MySQL | `#4479A1` |
| MongoDB | `#47A248` |
| Redis | `#DC382D` |
| Elasticsearch | `#005571` |
| Cassandra | `#1287B1` |
| Neo4j | `#008CC1` |
| SQLite | `#003B57` |

### Message Queues & Streaming

| Product | Color |
|---------|-------|
| Apache Kafka | `#231F20` |
| RabbitMQ | `#FF6600` |
| AWS SQS | `#FF9900` |
| NATS | `#27AAE1` |
| Pulsar | `#188FFF` |

### Cloud & Infra

| Product | Color |
|---------|-------|
| AWS | `#FF9900` |
| GCP | `#4285F4` |
| Azure | `#0089D6` |
| Cloudflare | `#F48120` |
| Vercel | `#000000` |
| Docker | `#2496ED` |
| Kubernetes | `#326CE5` |
| Terraform | `#7B42BC` |
| Nginx | `#009639` |
| FastAPI | `#009688` |

### Observability

| Product | Color |
|---------|-------|
| Grafana | `#F46800` |
| Prometheus | `#E6522C` |
| Datadog | `#632CA6` |
| LangSmith | `#1C3C3C` |
| Langfuse | `#6366F1` |
| Arize | `#6B48FF` |

---

Azure service colors → `references/product-colors-azure.md`
