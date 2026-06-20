# AGENTS.md — LLM Relay (APILLM)

> AI agent reference for the APILLM project — an LLM API relay/proxy that sits in front of multiple upstream model providers, monitors pricing, intelligently routes to the cheapest available upstream, and presents a unified OpenAI-compatible interface.

## Build / Test / Lint

```bash
# Install dependencies (editable)
pip install -e ".[dev]"

# Run the dev server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Lint (ignore line-length and unused-import noise)
ruff check app/ scripts/ --ignore=E501,F401

# Syntax check
python -m compileall app/ scripts/

# Database migrations
python -m alembic upgrade head

# Create a test user + API key
python scripts/create_user.py

# Smoke tests (require running server on :8000 + PostgreSQL + Redis)
python scripts/smoke_test.py
python scripts/smoke_test_phase2.py

# Frontend verification (requires server on :8000 + Playwright)
python Web/test_verify.py
```

**Critical environment variables** (see `.env.example`):
- `DATABASE_URL` — PostgreSQL async connection string (`postgresql+asyncpg://...`)
- `REDIS_URL` — Redis connection string
- `SECRET_KEY` — used as HMAC pepper for API key hashing

## Architecture

The project follows a **layered FastAPI architecture** with a proxy pattern:

```
Client (OpenAI SDK) → FastAPI Router → Auth Deps → Router Service → Proxy Handler → Upstream
                                                       ↕
                                                  Redis (prices, health)
```

### Module Tree

```
app/
├── main.py              FastAPI app + lifespan (Redis init, background loops)
├── api/
│   ├── deps.py          FastAPI dependency: HTTPBearer → authenticate()
│   ├── health.py        GET /health — dynamic Redis+DB ping, returns degraded on failure
│   └── v1/
│       ├── chat.py      POST /v1/chat/completions — proxy with price-smart routing + health-aware failover
│       └── models.py    GET /v1/models — concurrent upstream model aggregation with Semaphore
├── core/
│   ├── config.py        Pydantic Settings from env (pool sizes, timeouts, intervals)
│   ├── exceptions.py    AppError (HTTPException subclass) + ProxyError (bare Exception for SSE safety)
│   └── logging.py       structlog setup (JSON in prod, Console in debug)
├── db/
│   ├── base.py          SQLAlchemy async engine + session factory
│   ├── models.py        User, ApiKey, Upstream ORM models
│   └── repositories/    BaseRepository[T] + UserRepository, UpstreamRepository
├── schemas/
│   ├── openai.py        OpenAI-compatible request/response Pydantic models (all extra="forbid")
│   └── anthropic.py     Anthropic protocol models + bidirectional conversion functions
└── services/
    ├── auth.py          HMAC-SHA256 API key hashing + prefix strip + throttled last_used_at writes
    ├── router.py        Priority routing + price-sorted smart routing (reads Redis price cache)
    ├── redis.py         Async Redis wrapper with auto-reconnect, crash-safe cache_* functions
    ├── price_fetcher.py Background loop: scrape upstream /v1/models, cache pricing in Redis
    ├── health_checker.py Background loop: ping upstreams, state machine (healthy/degraded/unhealthy) in Redis
    └── proxy/
        ├── base.py      BaseProxyHandler ABC, shared httpx client, build_url, auth_header
        ├── openai_proxy.py   Pass-through proxy with SSE streaming
        └── anthropic_proxy.py Anthropic↔OpenAI bidirectional protocol translation + SSE

Web/                        # Frontend Dashboard (纯静态, zero-dependency)
├── index.html              # Main page: Hero matrix + Health + Models + Playground + Quick Start
├── css/
│   └── style.css           # Dark OLED minimal + 4-layer text matrix animation
├── js/
│   ├── api.js              # API client (IIFE): fetch wrapper, Bearer auth, SSE stream parser
│   └── app.js              # App logic: health polling (30s), models loader, Chat Playground
├── test_verify.py          # Playwright automated verification script
└── README.md

design-system/              # UI/UX design documentation (UI/UX Pro Max skill output)
└── apillm-relay/
    ├── MASTER.md           # Global design system (colors, fonts, components, anti-patterns)
    └── pages/
        └── landing.md      # Landing page detailed design spec
```

### Data Flow

1. **Auth**: Bearer token → strip `sk-relay-` prefix → HMAC-SHA256 hash → DB lookup (selectinload User)
2. **Chat routing**: `rank_upstreams_by_model()` → Redis MGET price cache → sort cheapest-first → filter unhealthy via Redis health state → try `max_retries` upstreams with failover
3. **Health**: Background loop pings all upstreams, updates Redis state machine, toggles `Upstream.is_enabled` in DB on threshold cross
4. **Price**: Background loop fetches `/v1/models` from each upstream, extracts pricing via configurable JSON paths, stores in Redis with TTL

## Key Files & Directories

| Path | Purpose |
|------|---------|
| `app/main.py` | Entry point; lifespan manages Redis init, background task spawn, graceful shutdown |
| `app/core/config.py` | Single source of truth for all settings (read from env) |
| `app/core/exceptions.py` | **ProxyError must NOT inherit HTTPException** — Starlette kills SSE connections |
| `app/services/router.py` | `rank_upstreams_by_model()` is the core routing decision; `select_upstream()` is legacy priority-only |
| `app/services/redis.py` | `cache_*` functions are **now crash-safe** — return `None`/`[]`/`0` on Redis failure |
| `app/services/auth.py` | `hash_key()` uses HMAC-SHA256 with `settings.secret_key` as pepper |
| `app/api/v1/chat.py` | `chat_completions` has top-level try/except now; health filtering lives inline here (not yet extracted) |
| `scripts/smoke_test.py` | Phase 1 smoke tests — needs running server, PostgreSQL, Redis |
| `scripts/smoke_test_phase2.py` | Phase 2 smoke tests — starts its own mock upstream on port 18081 |
| `.github/workflows/ci.yml` | CI: lint → syntax → migrations → start uvicorn → smoke tests |
| `Web/index.html` | Frontend Dashboard: Hero matrix, health panel, model grid, Chat Playground, Quick Start |
| `Web/js/api.js` | API client layer: fetch wrapper, Bearer auth, SSE stream parser, localStorage config |
| `Web/js/app.js` | Application logic: health polling (30s), model loading, Chat Playground (stream/non-stream) |
| `Web/css/style.css` | Dark OLED minimal stylesheet + 4-layer MiMo-style text matrix animation |
| `Web/test_verify.py` | Playwright automated frontend verification script |
| `design-system/apillm-relay/MASTER.md` | Global design system (colors, fonts, components, anti-patterns) |

## Coding Conventions

- **Async-first**: all I/O uses `async`/`await`; no sync blocking calls
- **Error handling**: Proxy errors use `raise ProxyError(msg) from e` (exception chain preserved); SSE streams must catch both httpx errors AND `json.JSONDecodeError`/`ValidationError` and yield error events
- **Pydantic**: all models use `model_config = ConfigDict(extra="forbid")`; key string fields have `max_length`
- **Type annotations**: used throughout; `cache_*` return types are `Any | None` (not `dict | None`)
- **Module-level globals**: httpx clients, Redis client, and handler dict are module-level singletons — this is a **known architectural debt** (ADR-4) that blocks unit testing
- **Ruff lint**: run with `--ignore=E501,F401`; scripts with `sys.path.insert` need `# noqa: E402` on subsequent imports
- **Tests**: no `tests/` directory yet; only smoke scripts exist. Test infrastructure is Phase 3.5 work

## Git Workflow

- Branch: `main` (direct pushes, no PR requirement currently)
- Commit style: `type: 中文描述` (e.g., `fix:`, `feat:`, `docs:`)
- CI triggers on push to `main`

## CI/CD

`.github/workflows/ci.yml` runs on every push to `main`:

1. Spin up PostgreSQL 16 + Redis 7 service containers
2. `ruff check app/ scripts/ --ignore=E501,F401`
3. `python -m compileall app/ scripts/`
4. `alembic upgrade head`
5. Start `uvicorn` in background, poll `/health` until ready (max 30s)
6. `scripts/smoke_test.py` (Phase 1)
7. `scripts/smoke_test_phase2.py` (Phase 2)
8. `pkill uvicorn` (always runs, even on failure)

**Pip caching** uses `actions/cache@v4` keyed on `pyproject.toml` hash.

## Tips for AI Agents

### Common pitfalls
- **Never convert `ProxyError` to an HTTPException subclass** — it will break SSE streaming (see ADR-1 in `findings.md`).
- **`get_redis()` is async** — must be awaited; it auto-reconnects on ping failure. If you see sync `get_redis()` calls, fix them.
- **API key hashing is HMAC-SHA256 with `settings.secret_key`** — plain SHA-256 was replaced in Phase 2.5. Smoke test scripts must use the same HMAC.
- **Health check endpoint returns `{"status": "ok", "redis": "...", "db": "..."}`** — not just `{"status": "ok"}`.
- **Streaming failover**: `_stream()` generator must catch `Exception` broadly and yield an SSE error event; unhandled exceptions cause silent SSE disconnection.
- **`rank_upstreams_by_model` sorts cheapest-first**, then filters unhealthy to the end. No price data → falls back to priority order.
- **`asyncio.gather` in models.py/price_fetcher.py/health_checker.py** is now wrapped with `asyncio.Semaphore(10)` — don't remove it without adjusting config.

### Where to look
- Adding a new upstream protocol → `app/services/proxy/` (extend BaseProxyHandler) + `app/db/models.py` (add enum) + `app/schemas/` (new protocol schema)
- Debugging routing → `app/services/router.py:rank_upstreams_by_model()`
- Debugging auth → `app/services/auth.py` (HMAC, prefix strip, last_used_at throttle)
- Configuration changes → `app/core/config.py` (add field; env var auto-mapped)
- Database changes → `app/db/models.py` (ORM) + `alembic/versions/` (new migration)

### Known architectural debt (see `findings.md` for details)
- **ADR-4**: Module-level global state (HTTP clients, Redis client) blocks unit test isolation. Future: dependency injection via FastAPI `Depends`.
- **ADR-5**: Health-check data flows into Redis but routing reads it inline in `chat.py` — not a clean service layer.
- **No unit tests**: full test infrastructure (pytest, conftest, `tests/` dir) is Phase 3.5 work.
