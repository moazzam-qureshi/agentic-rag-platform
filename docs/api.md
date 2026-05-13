# API reference

All endpoints are JSON. Authentication is by *trusted client IP* — no
accounts, no tokens. Each request is scoped to the IP that produced it.

Interactive OpenAPI docs are at `/docs` and `/redoc` when the API is running.

## `GET /health`

Liveness probe. Returns `200 {"status": "ok"}` whenever uvicorn is up.

## `POST /upload`

Accept a document upload, validate it, and enqueue async VLM ingestion.

**Form fields**
| field | type | required | notes |
|-------|------|----------|-------|
| `file` | binary | yes | PDF, DOCX, DOC, XLSX, or XLS |
| `turnstile_token` | string | when `TURNSTILE_SECRET` is set | Cloudflare Turnstile token |

**Guardrails applied in order**
1. Turnstile verification (if `TURNSTILE_SECRET` is set)
2. File-extension whitelist
3. Per-IP daily upload-count ceiling (`UPLOAD_MAX_PER_IP_PER_DAY`)
4. Page-count ceiling per doc (`UPLOAD_MAX_PAGES_PER_DOC`)
5. Per-IP daily VLM-page cost ceiling

**`200`**
```json
{
  "document_id": "uuid",
  "filename": "spec.pdf",
  "page_count_estimate": 14,
  "status": "pending",
  "message_id": "dramatiq-msg-id"
}
```

**Error responses**
- `400` empty file or unreadable document
- `403` Turnstile failed
- `413` page count exceeds the per-doc limit
- `415` unsupported file type
- `429` daily upload count or daily VLM-page ceiling exceeded

## `GET /documents`

List the calling IP's documents (excluding deleted ones).

**`200`**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "spec.pdf",
      "status": "indexed",
      "page_count": 14,
      "created_at": "2026-05-13T18:42:00Z",
      "expires_at": "2026-05-14T18:42:00Z",
      "error_message": null
    }
  ]
}
```

`status` is one of `pending` · `processing` · `indexed` · `failed` · `deleted`.

## `DELETE /documents/{document_id}`

Soft-delete the document for the caller and purge its OpenSearch pages.

**`200`**
```json
{
  "document_id": "uuid",
  "pages_deleted": 14,
  "status": "deleted"
}
```

**`404`** — the doc doesn't exist or doesn't belong to the calling IP.

## `GET /jobs/{document_id}`

Ingestion progress polling. The frontend hits this every ~1.5s while a
document is in `pending` or `processing`.

**`200`**
```json
{
  "document_id": "uuid",
  "filename": "spec.pdf",
  "status": "processing",
  "page_count": 0,
  "error_message": null,
  "logs": [
    {
      "level": "info",
      "message": "Starting ingestion: spec.pdf",
      "created_at": "2026-05-13T18:42:01Z"
    },
    {
      "level": "info",
      "message": "Decoded file content: 482113 bytes",
      "created_at": "2026-05-13T18:42:01Z"
    },
    {
      "level": "info",
      "message": "Parsing with VLM and indexing to OpenSearch...",
      "created_at": "2026-05-13T18:42:02Z"
    }
  ]
}
```

## `POST /chat`

Stream the agent's response as newline-delimited JSON events.

**Request**
```json
{
  "message": "What's the warranty policy?",
  "session_id": "optional-session-uuid"
}
```

If `session_id` is omitted, the API creates a fresh one and returns it in
the first `session` event.

**Response** — `application/x-ndjson`. Each line is one event:

```jsonl
{"event":"session","data":{"session_id":"..."}}
{"event":"status","data":{"status":"searching"}}
{"event":"tool_call","data":{"tool":"search"}}
{"event":"tool_result","data":{"tool":"search","result_count":3,"citations":[{"citation":"spec.pdf, Page 4","summary":"Warranty terms and conditions..."}],"documents_searched":["spec.pdf"]}}
{"event":"status","data":{"status":"generating"}}
{"event":"messages","data":{"content":"The "}}
{"event":"messages","data":{"content":"warranty "}}
{"event":"messages","data":{"content":"policy "}}
…
{"event":"done","data":{}}
```

**Event types**
- `session` — emitted once, contains the session_id (new or echoed)
- `status` — UI hint: `"searching"` then `"generating"`
- `tool_call` — agent committed to a tool invocation
- `tool_result` — tool returned, includes citations + documents searched
- `messages` — one assistant token (concatenate for the full answer)
- `done` — terminal success
- `error` — terminal failure

Errors during the stream still emit a final `error` event before the
connection closes; the HTTP status is `200` because the failure happens
mid-stream.
