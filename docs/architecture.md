# Architecture

DocuAI is a multi-service agentic RAG system: vision-LLM page extraction up
front, hybrid search retrieval at query time, LangGraph agent at the top,
streamed back to the browser with a live retrieval-trace panel.

## System diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                              Browser                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Next.js 16 / React 19  ·  Tailwind 4  ·  Notion-style UI     │  │
│  │                                                              │  │
│  │  Sidebar (uploads, docs)      Chat (markdown + streaming)    │  │
│  │  Right rail (retrieval trace)                                │  │
│  └─────────────────────────────┬────────────────────────────────┘  │
│                                │ ndjson SSE / fetch                │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                         Coolify / Traefik
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
┌─────────────┐          ┌──────────────┐          ┌──────────────┐
│   web       │          │   api        │          │   migrate    │
│ (Next.js    │          │  FastAPI     │          │  alembic     │
│  standalone)│          │  uvicorn     │          │  upgrade head│
└─────────────┘          └──────┬───────┘          └──────┬───────┘
                                │                         │
            ┌───────────────────┼─────────────────────────┘
            │                   │
            │            enqueues
            │            VLM jobs
            ▼                   ▼
    ┌───────────────┐    ┌──────────────┐         ┌──────────────┐
    │  postgres 16  │    │  redis 7     │◀────────│  scheduler   │
    │  (alembic-    │    │  (Dramatiq   │ hourly  │  APScheduler │
    │   managed)    │    │   broker)    │ cleanup │  enqueue     │
    └───────────────┘    └──────┬───────┘         └──────────────┘
                                │
                                ▼
                       ┌────────────────────────┐
                       │  worker (Dramatiq)     │
                       │  ────────────────      │
                       │  ingest_uploaded_doc:  │
                       │    1. base64 decode    │
                       │    2. PyMuPDF render   │
                       │       page-by-page     │
                       │    3. Qwen 2.5 VL via  │
                       │       OpenRouter +     │
                       │       Instructor       │
                       │    4. embed summaries  │
                       │       (MiniLM-L6, 384) │
                       │    5. bulk index       │
                       │                        │
                       │  cleanup_expired_docs: │
                       │    purge 24h-old data  │
                       └────────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  opensearch 2.18       │
                       │  documents_pages index │
                       │  BM25 + kNN (HNSW)     │
                       │  70/30 normalisation   │
                       └────────────────────────┘
```

## Indexing pipeline

A single Document → many Pages. Each page is processed independently.

1. **Render** — PyMuPDF rasterises the page at 200 DPI. For DOCX/XLSX the
   doc is converted to PDF via LibreOffice headless first.
2. **Extract** — the page image goes to a vision-LLM (Qwen 2.5 VL 72B via
   OpenRouter) with an Instructor-validated Pydantic schema:
   - `skip` — drop cover/title/blank pages from the index
   - `summary` — short retrieval description
   - `full_content` — exhaustive verbatim markdown for answering
3. **Embed** — `sentence-transformers/all-MiniLM-L6-v2` encodes the summary
   to a 384-dim vector (CPU-only; ~50ms/page).
4. **Index** — bulk write to `documents_pages` in OpenSearch. The `summary`
   field is BM25-indexed (English analyzer); `summary_embedding` is kNN-
   indexed with HNSW. `full_content` is stored but not indexed.

## Query pipeline

1. **Translate (optional)** — the agent invokes the `translate_query` tool
   if the user message isn't English. The index is English-only.
2. **Hybrid retrieval** — `search` tool issues a hybrid query to the
   `documents_pages` index. BM25 + kNN scores are combined by a Min-Max
   normalisation processor with 0.7/0.3 weighting.
3. **Answer** — the LLM (`gpt-4o-mini` by default) sees `full_content` for
   each retrieved page plus the system prompt enforcing verbatim quoting
   and `[Filename, Page X]` citations.
4. **Stream** — every step (tool call, tool result, response token) is
   streamed back as ndjson SSE events. The frontend renders chat tokens
   into the main panel and tool calls/citations into the retrieval-trace
   panel as they arrive.

## Guardrails

A layered defence sits in front of every public endpoint. The same contract
is implemented in every project in this portfolio.

| Layer | Implementation |
|-------|----------------|
| Trusted-proxy IP | `TrustedProxyMiddleware`. Reads `X-Forwarded-For` only when peer is in a configured trusted CIDR. |
| Per-IP rate limit | slowapi + Redis sliding window. Defaults: 30/hr, 100/day. |
| Per-IP cost ceiling | Redis Lua-atomic counter, keyed on (IP, YYYY-MM-DD). Caps VLM page units, not just request count. |
| Worker concurrency | Dramatiq `--threads 2`. Caps simultaneous VLM jobs cluster-wide. |
| Turnstile (uploads) | Cloudflare siteverify on `/upload` only. Chat stays frictionless. |
| 24h auto-delete | APScheduler enqueues `cleanup_expired_documents` hourly. |
| LLM token cap | `LLM_MAX_TOKENS_DEFAULT=1024`. |

## Why this design over a generic RAG starter

1. **No chunking.** Most "chat with PDF" demos chunk text by paragraph or
   token count. Tables get fragmented, multi-page sections lose context,
   layout-sensitive content (specs, dimensions, captions) gets butchered.
   Page-level VLM extraction preserves the full visual context of each page
   and stores it verbatim — at the cost of more upfront VLM tokens.
2. **Hybrid search over summaries, full content for answering.** Indexing
   the long `full_content` directly produces noisy search results — long
   pages with one relevant sentence overshadow short, focused pages. Indexing
   *summaries* (which the VLM was prompted to make retrieval-optimised) and
   returning *full content* gets both: precise retrieval, exhaustive answers.
3. **Visible retrieval trace.** Most agentic UIs hide the tool-calling step.
   Surfacing it (right rail) turns "AI magic" into auditable behaviour —
   important both for trust and for the demo positioning.
