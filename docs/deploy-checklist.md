# Coolify deploy checklist

Use this for the very first deploy. Future deploys are just `git push`.

## 0 · Prereqs

- [ ] Coolify v4+ running on your VPS
- [ ] DNS for `docuai.<yourdomain>` pointing at the VPS IP
- [ ] OpenAI API key with credit
- [ ] OpenRouter API key with credit (covers Qwen 2.5 VL)
- [ ] Optional: Cloudflare Turnstile site/secret pair

## 1 · Create the Coolify project

1. Coolify → **Projects** → **+ New** → name: `DocuAI`.
2. Inside the project → **+ New Resource** → **Docker Compose (from Git)**.
3. Repository: `https://github.com/moazzam-qureshi/agentic-rag-platform`
4. Branch: `main`
5. Compose file path: `docker-compose.yml` (default)

## 2 · Set environment variables

Coolify → resource → **Environment Variables**. Paste this block, fill in
the real values:

```
# Persistence — keep as-is, hostnames resolve inside the compose network
DATABASE_URL=postgresql+asyncpg://docuai:docuai@postgres:5432/docuai
REDIS_URL=redis://redis:6379/0
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=documents

# LLMs — required
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=qwen/qwen2.5-vl-72b-instruct

# Guardrails — tune to taste
TRUSTED_PROXIES=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
RATE_LIMIT_PER_HOUR=30
RATE_LIMIT_PER_DAY=100
UPLOAD_MAX_PER_IP_PER_DAY=3
UPLOAD_MAX_PAGES_PER_DOC=20
WORKER_MAX_CONCURRENCY=2
DOCUMENT_TTL_HOURS=24
LLM_MAX_TOKENS_DEFAULT=1024

# Cloudflare Turnstile (leave blank to skip CAPTCHA in dev)
TURNSTILE_SECRET=
TURNSTILE_SITEKEY=
NEXT_PUBLIC_TURNSTILE_SITEKEY=

# Frontend API base — empty so the browser hits same-origin
NEXT_PUBLIC_API_BASE_URL=

LOG_LEVEL=INFO
SERVICE_NAME=docuai-api
```

## 3 · Configure domains

Coolify generates Traefik labels for each service exposed in compose. You
want **two** domains routed:

| Domain | Service | Port |
|--------|---------|------|
| `docuai.<yourdomain>` | `web` | 3000 |
| `docuai.<yourdomain>/api/*` | `api` | 8000 |

In Coolify's **Domains** tab for the resource:

1. Add `https://docuai.<yourdomain>` → bind to `web` → port `3000`.
2. Same domain again but with path prefix `/api` → bind to `api` → port
   `8000`.

> Coolify rewrites the path: the browser hits `/api/upload`, Traefik strips
> `/api` and forwards `/upload` to the api container. That matches the
> FastAPI route names.
>
> If Coolify's UI doesn't expose path-prefix routing directly, add a custom
> Traefik label on the `api` service:
> ```
> traefik.http.middlewares.docuai-stripapi.stripprefix.prefixes=/api
> traefik.http.routers.docuai-api.middlewares=docuai-stripapi
> ```

SSL is automatic via Let's Encrypt.

> If you prefer a fully separate `api.docuai.<yourdomain>`, set the build
> arg `NEXT_PUBLIC_API_BASE_URL=https://api.docuai.<yourdomain>` on the
> `web` service.

## 4 · Deploy

Click **Deploy**. First build takes ~10 minutes:

- OpenSearch 2.18 image pull (~700 MB)
- PyTorch wheels for sentence-transformers (~700 MB)
- Next.js production build

Watch the **Logs** tab. Expected sequence:

1. Images build
2. Postgres + Redis + OpenSearch start, pass healthchecks
3. `migrate` runs `alembic upgrade head`, exits 0
4. `api`, `worker`, `scheduler`, `web` start
5. Healthchecks pass on `web` (port 3000) and `api` (port 8000)

## 5 · Smoke test

From **incognito** in a separate network (mobile hotspot):

1. Hit `https://docuai.<yourdomain>` → hero renders, sidebar visible.
2. Upload a small PDF (~3 pages).
3. Sidebar entry transitions `queued` → `indexing…` → `3 pages` within
   ~30 seconds. (First doc is slower — VLM cold start.)
4. Ask: *"Summarize this document in three sentences."*
5. Right rail shows `search` tool call → tool result with citations.
6. Main pane streams an answer with `[filename.pdf, Page N]` citations.

If any step hangs:

```bash
# In Coolify → Logs → pick the service
docker logs docuai-api
docker logs docuai-worker
docker logs docuai-opensearch
```

The most common first-deploy issues:

| Symptom | Fix |
|---------|-----|
| `migrate` fails with `Connection refused` | postgres not healthy yet; just redeploy, depends_on/healthcheck handles it on retry |
| OpenSearch OOM-killed | Bump VPS RAM or drop heap to `-Xms512m -Xmx512m` |
| Upload returns 403 | Turnstile secret missing or invalid |
| Chat returns nothing | Check OPENAI_API_KEY has credit |
| Upload succeeds but never indexes | Check OPENROUTER_API_KEY |

## 6 · Post-deploy

- [ ] Add the live URL to the repo README at the top of this file
- [ ] Update Upwork profile → portfolio item → link the live demo URL
- [ ] Drop the case study (see `docs/upwork-case-study.md` once written)
- [ ] Optional: set monthly OpenRouter + OpenAI budget caps
