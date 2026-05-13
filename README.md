<div align="center">

# DocuAI

**Agentic RAG over your documents — vision-LLM page extraction, hybrid search, cited answers.**

[![CI](https://github.com/moazzam-qureshi/agentic-rag-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/moazzam-qureshi/agentic-rag-platform/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Try the demo →](https://docuai.yourdomain.com) · [Architecture](docs/architecture.md) · [API reference](docs/api.md) · [Deploy guide](docs/deploy.md)

</div>

---

DocuAI is an open-source agentic RAG system. Upload a PDF, DOCX, or
spreadsheet and ask questions grounded in the actual content of your
documents — with verbatim citations and a live retrieval trace.

What makes it different from a typical "chat with PDF" demo:

- **Vision-LLM page extraction, no chunking.** Each page is rendered to an
  image and a vision model (Qwen 2.5 VL 72B via OpenRouter) extracts both a
  short retrieval summary and exhaustive verbatim markdown for answering.
  Tables, multi-column layouts, captions, charts — all preserved.
- **Hybrid search done right.** OpenSearch index with BM25 + kNN over
  sentence-transformers embeddings, normalised with a 70/30 weighted
  min-max processor. BM25-only fallback when hybrid fails.
- **LangGraph agent with explicit tools.** `translate_query` for
  multilingual queries, `search` for hybrid retrieval. The agent's tool
  calls and the citations it pulls are streamed to a live retrieval-trace
  panel in the UI.
- **Production-grade guardrails.** Trusted-proxy IP detection, Redis-backed
  per-IP sliding-window rate limits, atomic per-IP daily cost ceilings,
  Cloudflare Turnstile on uploads, capped LLM token budgets, hourly cleanup
  of uploads older than 24h.

## Stack

```
Frontend         Next.js 16 · React 19 · Tailwind 4 · TypeScript
                 Notion-inspired UI · streaming SSE consumer

API              FastAPI · uvicorn · slowapi · sse-starlette

Agent            LangGraph · LangChain · OpenAI (chat) ·
                 Qwen 2.5 VL via OpenRouter (vision)

Storage          PostgreSQL 16 (alembic) · OpenSearch 2.18 (BM25 + kNN)

Queue            Dramatiq · Redis 7 · APScheduler

Deploy           Docker Compose · Coolify
```

## Local development

Requires Docker 26+, `uv` for Python, and Node 22+.

```bash
# 1. Spin up Postgres, Redis, OpenSearch
docker compose -f docker-compose.dev.yml up -d

# 2. Install Python deps
uv sync

# 3. Apply migrations
DATABASE_URL="postgresql+asyncpg://docuai:docuai@localhost:5432/docuai" \
  uv run alembic upgrade head

# 4. Run the API
PYTHONPATH=services/api/src:services/worker/src:. \
  uv run uvicorn api.main:app --reload --port 8000

# 5. Run the worker (separate terminal)
PYTHONPATH=services/api/src:services/worker/src:. \
  uv run dramatiq worker.main --threads 2

# 6. Run the web
cd web && npm install && npm run dev
```

Visit `http://localhost:3000`. Without `TURNSTILE_SECRET` in `.env`,
uploads bypass the CAPTCHA gate.

## Project layout

```
agentic-rag-platform/
├── shared/                       # Cross-service Python packages
│   ├── indexing/                   VLM page extraction + OpenSearch indexer
│   ├── db_models/                  SQLAlchemy models (Document, ChatSession, …)
│   ├── tasks/                      Dramatiq actors (ingest, cleanup)
│   └── guardrails/                 Rate limit + cost ceiling + Turnstile + proxy
│
├── services/
│   ├── api/                        FastAPI service
│   │   └── src/api/
│   │       ├── main.py             App entry: middleware → limiter → routes
│   │       ├── routes/             /health /upload /documents /jobs /chat
│   │       ├── agent/              LangGraph agent + tools + prompts + memory
│   │       └── db/                 Async session + OpenSearch store
│   │
│   └── worker/                     Dramatiq worker + APScheduler entry-points
│       └── src/worker/
│           ├── main.py             Worker process target
│           ├── scheduler.py        Hourly cleanup scheduler
│           └── db/                 Sync session for actor bodies
│
├── web/                            Next.js 16 frontend
│   └── src/
│       ├── app/                    Page + layout + global CSS tokens
│       ├── components/             AppShell, Sidebar, ChatPanel, RetrievalTrace…
│       ├── hooks/                  useChat (context), useDocuments
│       └── lib/                    Typed API client, Turnstile, class utils
│
├── alembic/                        Migrations
├── docs/                           architecture, api, deploy
├── docker-compose.yml              Production compose (Coolify)
├── docker-compose.dev.yml          Local infra only (no app containers)
├── pyproject.toml                  Python deps + uv lock
└── .env.example                    Documented env vars
```

## Production deploy

DocuAI is one `git push` away from a deploy on [Coolify](https://coolify.io).
See [docs/deploy.md](docs/deploy.md) for the full walkthrough.

## License

MIT. See [LICENSE](LICENSE).

---

<div align="center">

Built by **Moazzam Qureshi** · [GitHub](https://github.com/moazzam-qureshi)

</div>
