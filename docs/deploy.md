# Deploying DocuAI on Coolify

DocuAI is a docker-compose application. Coolify v4+ deploys it natively from
a Git push.

## Prerequisites

- Coolify v4+ on a VPS with at least:
  - 4 GB RAM (OpenSearch alone uses 1 GB heap; PyMuPDF + sentence-transformers
    need another ~1 GB headroom)
  - 20 GB disk (postgres + opensearch volumes + image layers)
  - Docker 26+ with Compose v2
- An OpenAI API key and an OpenRouter API key
- Optional: a Cloudflare Turnstile site/secret pair (`TURNSTILE_SITEKEY` /
  `TURNSTILE_SECRET`)

## Steps

### 1. Add the project to Coolify

In Coolify → **Projects** → **Add new** → **Docker Compose** based on Git:

- Source: `github.com/moazzam-qureshi/agentic-rag-platform`
- Branch: `main`
- Build pack: Docker Compose
- Compose file: `docker-compose.yml`

### 2. Configure the domain

In the project's **General** tab:

- Add a domain (e.g. `docuai.yourdomain.com`).
- Bind it to the `web` service on port `3000`.
- Coolify will provision SSL via Let's Encrypt automatically.

The `api` service is internal only. The browser hits the same origin and
Coolify's Traefik routes to `api` based on the path (this works out of the
box for our setup because the frontend uses relative URLs).

> If you prefer a separate `api.yourdomain.com`, expose both services and
> set `NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com` as a build arg
> on the `web` service.

### 3. Environment variables

Copy `.env.example` into Coolify's **Environment variables** UI for the
project. At minimum you must set:

```
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

Recommended for production:

```
TURNSTILE_SECRET=...           # from Cloudflare dashboard
TURNSTILE_SITEKEY=...
NEXT_PUBLIC_TURNSTILE_SITEKEY=...  # same as TURNSTILE_SITEKEY
TRUSTED_PROXIES=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

Leave the rest at defaults unless you have a reason to change them.

### 4. Deploy

Click **Deploy**. Coolify will:

1. Clone the repo
2. Build six images (web, api, worker, scheduler, migrate, plus
   postgres/redis/opensearch pulled prebuilt)
3. Run the `migrate` service to apply alembic migrations
4. Start postgres, redis, opensearch and wait for healthchecks
5. Start api, worker, scheduler, web

First deploy takes ~10 minutes because of:
- OpenSearch image (~700 MB)
- PyTorch wheels for sentence-transformers (~700 MB)
- Next.js production bundle build

Subsequent deploys reuse the layer cache.

### 5. Verify

From an incognito window on a different network:

1. Visit `https://docuai.yourdomain.com`.
2. The hero renders. Upload a small PDF.
3. The sidebar shows it transition through `queued` → `indexing…` → `n pages`.
4. Ask a question. The right rail lights up with the tool call, the answer
   streams into the main pane, citations appear in both.

Logs for any service: `docker logs <coolify-container-name>`, or use Coolify's
**Logs** tab.

## Operational notes

### Migrations on subsequent deploys

The `migrate` service is declared as a one-shot (`restart: "no"`) that runs
`alembic upgrade head` and exits. Coolify re-runs it on every deploy. Any
new alembic revision lands automatically.

### Volumes

- `docuai_pg_data` — Postgres data
- `docuai_os_data` — OpenSearch indices

Both are Coolify-tracked named volumes. Persist across deploys; remove
manually in Coolify's volume UI if you ever want a clean slate.

### Scaling

The defaults are tuned for a small VPS:

- One worker container, two threads → max 2 concurrent VLM jobs
- OpenSearch heap = 1 GB (single node, single shard)

To scale up, increase `WORKER_MAX_CONCURRENCY` and bump the `--threads` arg
in `docker-compose.yml`'s `worker` command. For real throughput you'd run
multiple worker replicas — but at that point you're past "demo" and want
to revisit the data model anyway.

### Cost monitoring

OpenRouter charges per VLM call. The guardrails cap per-IP daily VLM page
consumption, but at scale you'll want a hard ceiling on OpenRouter spend
itself — set a monthly budget in your OpenRouter account dashboard.
