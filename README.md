# DocuAI — Agentic RAG over your documents

> **Status:** Work in progress. The full demo (web UI + live deploy) is being built. This repo currently contains the document indexing pipeline (vision-LLM page extraction + hybrid search). API service, worker, and web UI are coming in subsequent commits.

DocuAI is an agentic RAG system that lets you upload PDFs, DOCX, or spreadsheets and ask questions grounded in your documents, with cited answers and a visible retrieval trace.

## What makes it different from a typical "chat with PDF" demo

- **Vision-LLM page extraction (no chunking).** Each page is rendered as an image and a vision model (Qwen 2.5 VL 72B by default, via OpenRouter) extracts both a short summary (for retrieval) and an exhaustive verbatim markdown (for answering). No chunking artifacts, no lost tables, no broken layouts.
- **Hybrid search.** OpenSearch index with BM25 + kNN (sentence-transformers all-MiniLM-L6-v2), normalized with a 70/30 weighted min-max processor.
- **LangGraph agent with explicit tools.** Translation, hybrid search, and (when needed) the MCP `sequentialthinking` server for persistent reasoning. All tool calls are streamed to the UI as a retrieval trace.

## Live demo

Coming soon at `https://docuai.<domain>` — link will be added once Coolify deploy is verified.

## License

MIT. See [LICENSE](LICENSE).
