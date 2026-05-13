# Upwork case study — DocuAI

Drop this as a portfolio item on your Upwork profile. Trim to the section
sizes Upwork allows; everything below is a superset.

---

## Title

> **DocuAI — Agentic RAG platform with vision-LLM page extraction and cited answers**

## Tagline (one-liner)

> Production-grade RAG demo. Upload any PDF or DOCX, ask anything, get
> answers with verbatim citations and a live retrieval trace.

## Try it

> 🔗 **Live demo:** https://docuai.<yourdomain>
> 🔗 **Open-source code:** https://github.com/moazzam-qureshi/agentic-rag-platform

No signup. Upload a document and ask a question in 10 seconds.

## What it does

DocuAI is a multi-tenant, agentic RAG system I built end-to-end:

- **Upload any PDF.** DocuAI renders every page as
  an image and uses a vision LLM (Qwen 2.5 VL via OpenRouter) to extract a
  retrieval summary plus exhaustive verbatim markdown — no chunking, no
  lost tables.
- **Ask questions in plain English** (or any language — there's a
  translation tool the agent calls when needed). The agent (LangGraph)
  decides when to search, what keywords to use, and answers grounded in
  the retrieved pages.
- **Watch it work.** Every tool call and every citation is streamed to a
  live right-rail panel — clients can audit exactly which pages the answer
  came from.

## Why it matters for clients

If you're hiring for AI work, you're asking a single question:

> *"Has this person actually built RAG that works in production?"*

Most freelancers can wire `LangChain.from_documents()` against `text-splitter`
and call it RAG. That's a tutorial, not a product. DocuAI is the version
that survives contact with real documents:

| Hard problem | How DocuAI handles it |
|--------------|------------------------|
| Tables and multi-column PDFs get butchered by text splitters | Vision LLM reads every page as an image; tables come back as proper markdown |
| Chunking loses context across page boundaries | Page-level indexing — entire pages are the unit |
| Search returns long irrelevant chunks | Index on short summaries, answer from full content |
| Demos die when a stranger hits them with a 100-page PDF | Per-IP rate limits, page-count ceilings, daily cost ceilings, Cloudflare Turnstile, async worker queue with concurrency caps |
| LLM costs surprise you on the first viral tweet | Redis-backed atomic cost counters, capped token budgets, 24h auto-deletion |
| "Where did that answer come from?" | Every assistant message is grounded in `[Filename, Page N]` citations the user can click through |

## How it's built

**Frontend.** Next.js 16 (Turbopack), React 19, Tailwind 4, TypeScript.
Notion-inspired three-pane UI: sidebar with document list and live
ingestion status, main chat with streamed markdown rendering, right rail
with the agent's tool calls and retrieved citations. The chat uses an
ndjson SSE stream so the user sees tokens flow as the model generates
them.

**API.** FastAPI on Python 3.13. Six routes: upload, list documents,
delete document, job status, chat (SSE), health. Layered guardrails on
every endpoint — trusted-proxy IP detection, slowapi sliding-window
rate limits backed by Redis, per-IP daily cost ceilings via atomic Redis
Lua scripts, optional Cloudflare Turnstile on the upload endpoint.

**Agent.** LangGraph + LangChain. Two custom tools: `translate_query`
(for multilingual queries) and `search` (hybrid retrieval). The agent
decides when to search, what to search for, and when it has enough to
answer.

**Indexing.** PyMuPDF renders each document page to a 200 DPI image.
LibreOffice headless handles DOCX/XLSX conversion. Each page goes through
Qwen 2.5 VL 72B via OpenRouter (with the `instructor` library for
validated structured output) and produces a retrieval summary plus
exhaustive verbatim markdown. Embeddings via sentence-transformers
all-MiniLM-L6-v2 (384 dimensions, CPU-only).

**Search.** OpenSearch 2.18 with hybrid retrieval — BM25 over English-
analyzed summaries plus kNN HNSW over the summary embeddings, normalised
70/30 by an OpenSearch search pipeline.

**Queue.** Dramatiq + Redis. The API enqueues VLM ingestion jobs; the
worker container processes them with bounded concurrency. APScheduler in
a separate container enqueues a hourly cleanup actor that purges
documents older than 24h.

**Persistence.** Postgres 16 (managed by Alembic). Models for documents,
chat sessions, messages, sync jobs, processing logs.

**Deploy.** Docker Compose on a VPS via Coolify. Eight services:
`web`, `api`, `worker`, `scheduler`, `migrate` (one-shot alembic),
`postgres`, `redis`, `opensearch`. Coolify handles domain routing, SSL,
and persistent volumes. Migrations re-run on every deploy.

**CI.** GitHub Actions. Ruff (lint + format) and an import smoke test on
the Python side; ESLint + `next build` on the frontend.

## What's interesting about the engineering

A few decisions that aren't obvious from reading the code:

1. **Vision-LLM extraction is one-shot per page, not chunked.** It's more
   expensive upfront, but it preserves *exactly* what's on the page —
   tables, captions, image text, charts. Most chunking-based RAG demos
   fail in spectacular ways on real-world enterprise documents; this one
   doesn't.

2. **Index on summaries, answer from full content.** Two-field design.
   The VLM produces both fields in the same call. Short summaries make
   BM25 + vector search precise (a 5-page section doesn't drown out a
   single relevant paragraph), while the LLM answers from the unabridged
   page content. Best of both.

3. **Anti-spoof IP detection.** A naïve `request.client.host` reads the
   Coolify Traefik IP, not the visitor's. Trusting `X-Forwarded-For`
   blindly lets anyone bypass per-IP rate limits with a header. The
   middleware reads `X-Forwarded-For` *only* if the immediate peer is in
   a configured trusted CIDR; otherwise it uses the raw peer IP.

4. **Per-IP cost ceiling separate from rate limit.** Rate limits cap
   request count; this caps *units of work* (VLM pages). A user can hit
   the request rate limit a hundred times without ever threatening cost,
   but a single 100-page PDF could blow a daily budget. The ceiling is
   an atomic Redis counter via a Lua script.

5. **Worker concurrency as the last line of defence.** Even if every
   other guardrail fails (rotated IPs, etc.), the Dramatiq worker is
   configured for at most N concurrent VLM jobs. Worst case is "the demo
   feels slow", not "I get a $500 surprise bill".

6. **Visible retrieval trace.** Most agent UIs hide the tool-calling step
   to keep the experience clean. I think that's the wrong tradeoff for a
   trust-building demo — surfacing the agent's calls and the citations it
   pulled turns "AI magic" into auditable behaviour.

## What I can build for you

If you have documents and need an AI layer that actually grounds its
answers in them — knowledge bases, technical documentation, contracts,
research papers, internal SOPs — DocuAI is roughly what production looks
like. I can adapt the same architecture to your specific domain in 1–3
weeks depending on scope.

Common variations I've shipped or can ship:

- Replace upload with a sync against your existing storage (S3, Google
  Drive, SharePoint, Notion, Confluence)
- Add per-user authentication and tenant isolation
- Swap models for self-hosted alternatives (e.g. local Qwen-VL via
  vLLM) if cost or compliance requires it
- Add a "feedback loop" where users mark answers as helpful/wrong and
  the system retrains its retrieval weights
- Add structured output extraction (invoices, contracts, lab reports) on
  top of the same vision pipeline

Reach out via Upwork — happy to scope a working prototype against your
real data in 48 hours.
