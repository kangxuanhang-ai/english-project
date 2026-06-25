# AGENTS.md

English learning platform — pnpm monorepo with Vue 3 frontend, Python FastAPI backend (two apps), client-side tracker library, and shared TypeScript packages. Comments throughout the codebase are in Chinese.

## Commands

### Install Dependencies
Root pnpm workspace and `server/` Python project are independent:
```bash
pnpm install                # from repo root (web, tracker, common, config)
cd server && uv sync        # Python backend (uv-managed, Python 3.12+)
```

### Start Development (from repo root)
- `pnpm all` — All services concurrently (web:8080, server:3000, ai:3001)
- `pnpm web` — Frontend only
- `pnpm server` — Main API server only
- `pnpm ai` — AI service only

### Frontend (apps/web)
- `pnpm dev` — Vite dev server
- `pnpm build` — vue-tsc type-check + vite build
- `pnpm type-check` — vue-tsc only

### Backend (from server/)
Python 3.12+, uv-managed, hatchling build backend. PyPI mirror configured to Tsinghua in `pyproject.toml`.
- `uv run python -m uvicorn app.main:socket_app --port 3000 --reload` — Main API
- `uv run python -m uvicorn ai.main:ai_app --port 3001 --reload` — AI service
- `uv run alembic upgrade head` — Run database migrations
- `uv run alembic revision --autogenerate -m "description"` — Generate new migration
- `uv run python seed.py` — Seed database with courses and word book data

### Tracker (apps/tracker)
- `pnpm build` — Library mode build (ES/CJS/UMD/IIFE)

## Architecture

### Workspace Structure
```
english/
├── apps/
│   ├── web/          # Vue 3 frontend (@en/web)
│   └── tracker/      # Client SDK (@en/tracker)
├── packages/
│   ├── common/       # Shared TypeScript types (@en/common)
│   └── config/       # Port constants (@en/config)
└── server/           # Python backend (not in pnpm workspace)
```

Root `package.json` defines convenience scripts via `concurrently`. The `server/` directory is a standalone uv-managed Python project — its dependencies, lockfiles, and `.venv` are completely independent from the pnpm workspace.

### Backend: Two FastAPI Apps
`server/` contains two FastAPI applications sharing a common `shared/` directory:

**app/** (port 3000): Main REST API. Routers: user, word_book, course, pay, learn, tracker. Socket.IO mounted as ASGI app via `socket_app = socketio.ASGIApp(sio, app)`. JWT auth with access/refresh tokens. Alipay payment (sandbox). Global middleware wraps all 2xx responses into `{timestamp, path, message, code, success, data}` envelope.

**ai/** (port 3001): AI service. Routers: chat, conversation, prompt, recommend. DeepSeek via LangChain with deep-thinking (reasoner) mode. LangGraph `create_react_agent` with PostgresCheckpointer for chat history. Bocha Search API for web grounding. APScheduler for digest jobs. Slowapi for rate limiting. Imports response envelope middleware and exception handlers from `app/middleware.py`. Chat accepts `deepThink` and `webSearch` flags (mutually exclusive — `deepThink` takes priority).

**shared/**: External service clients — MinIO (file storage), Alipay (payments), Email (SMTP). ClickHouse client exists but is empty (not functional yet).

**app/models/**: SQLAlchemy ORM models — User, WordBook, WordBookRecord, Course, CourseRecord, PaymentRecord, Visitor, PageView, TrackEvent, PerformanceEntry, ErrorEntry, Conversation.

**app/schemas/**: Pydantic request/response schemas, one per router domain.

**app/services/**: Business logic layer, one per router domain.

**alembic/**: Database migrations. Config in `alembic.ini`. Models imported in `alembic/env.py`.

### AI Chat Architecture

The AI service uses LangGraph `create_react_agent` with SSE streaming (`agent.astream_events`). The frontend receives events via `@microsoft/fetch-event-source` (not Axios). The response envelope middleware explicitly skips `/ai/v1/chat` paths to preserve the SSE stream.

**Chat roles**: `normal`, `master`, `business`, `qilinge`, `xiaoman` — each has a distinct system prompt. Only the `normal` role has access to AI tools.

**AI tools** (`ai/services/tools/`): `make_tools(user_id)` creates per-user tool instances:
- `word_lookup` — look up word definitions
- `web_search` — web search via Bocha API
- `grammar_check` — grammar checking
- `progress_query` — query user's learning progress
- `recommend` — learning recommendations

Other roles get an empty tool list.

**SSE client**: The frontend SSE client (`apps/web/src/apis/sse/index.ts`) calls `ensureValidToken()` before opening a connection (5-second expiry buffer), distinct from the Axios interceptor flow. The `onerror` handler throws to stop `fetchEventSource` from auto-retrying on failures.

### Configuration
Both apps use pydantic-settings reading from `server/.env`:
- `app/config.py` → `Settings` (full config: DB, JWT, MinIO, DeepSeek, Alipay, Email, ClickHouse)
- `ai/config.py` → `AISettings` (subset: DeepSeek, AI DB, Bocha, Email)

Port constants for dev servers are in `packages/config/index.ts` and used by Vite proxy config and root scripts.

### Frontend: Vue 3
Routes: Home, WordBook, Setting, Chat, Course. Views are in `src/views/` (not `src/pages/`). State via Pinia with localStorage persistence. API layer in `src/apis/`. Tailwind CSS 4 + Element Plus (Chinese locale `zh-cn`).

**Vite config** (`apps/web/vite.config.ts`): `@vitejs/plugin-vue` + `@tailwindcss/vite`. Path alias `@` → `./src`. Dev proxy rewrites `/api` → `localhost:3000` and `/ai` → `localhost:3001`.

**API routing**: Frontend Axios instances use base URLs `/api/v1` (server) and `/ai/v1` (ai). All API modules (`src/apis/auth/`, `src/apis/chat/`, etc.) import from `src/apis/index.ts` which exports `serverApi` and `aiApi` instances.

**JWT token refresh flow**: The Axios response interceptor in `src/apis/index.ts` handles 401s by refreshing the access token via a refresh token. Concurrent 401s are queued (`requestQueue`) while a single refresh is in flight — once the new token arrives, all queued requests retry with it. On refresh failure, the user is logged out and redirected to `/`. Access tokens expire in 15 minutes; the SSE client proactively refreshes ~5 seconds before expiry.

**Frontend hooks** (`src/hooks/`): `useAudio`, `useAvatar`, `useLogin`, `useSocket`, `useVoiceToText` (Web Speech API).

**3D/animation**: Three.js models in `components/Login/ModelViewer.vue` and `views/Home/components/Hologram.vue`. GSAP for animations. DOMPurify + marked for markdown rendering in chat.

### Tracker: @en/tracker
Client SDK reporting UV (FingerprintJS), PV, events, JS errors, Web Vitals. Exports a `Tracker` class with `setUserId(userId)` to associate visitors with logged-in users.

### Shared Packages
- `packages/common` (`@en/common`): Pure TypeScript type definitions, no runtime deps
- `packages/config` (`@en/config`): Port constants (3000, 3001, 8080)

## Database

PostgreSQL via SQLAlchemy async (asyncpg). Two databases: `english` (app data), `langchain` (AI chat history). ClickHouse for analytics (not yet functional — `shared/clickhouse_client.py` is empty).

Alembic manages migrations in `server/alembic/`. Models defined in `server/app/models/`.

**DATABASE_URL format**: Use standard `postgresql://` in `.env` — the app transforms it to `postgresql+asyncpg://` at runtime. The AI service uses a separate `AI_DATABASE_URL` for its LangChain checkpointer.

**Windows note**: The AI service (`ai/main.py`) sets `WindowsSelectorEventLoopPolicy` at startup, required for `psycopg` on Windows.

## Production Deployment

1. **Environment**
   - Copy `server/.env.example` → `server/.env` and `apps/web/.env.example` → `apps/web/.env.production`
   - Set a strong `SECRET_KEY` (not the example default)
   - Configure `ALIPAY_NOTIFY_URL` to a public HTTPS URL reachable by Alipay
   - Optional: `REDIS_URL`, `RATE_LIMIT_STORAGE_URI` for multi-worker rate limits / recommend cache

2. **Database**
   ```bash
   cd server && uv sync
   uv run alembic upgrade head
   uv run python seed.py
   ```
   Word book seed uses `server/data/ecdict.sample.csv` by default; set `ECDICT_CSV_PATH` for full ECDICT.

3. **Build frontend**
   ```bash
   pnpm install
   pnpm --filter @en/web build
   ```
   Deploy `apps/web/dist/` behind Nginx (or CDN).

4. **Run backends** (two processes, same `server/.env`):
   ```bash
   uv run python -m uvicorn app.main:socket_app --host 0.0.0.0 --port 3000
   uv run python -m uvicorn ai.main:ai_app --host 0.0.0.0 --port 3001
   ```
   Use `socket_app` for the main API (Socket.IO mounted). Do not use plain `app` in production if payments rely on WebSocket notify.

5. **Nginx** — see `docs/deploy/nginx.example.conf`: proxy `/api` → 3000, `/ai` → 3001 with SSE buffering off, `/socket.io` → 3000, SPA `try_files`.

6. **Health** — `GET /health` on the main API (port 3000) returns DB status; use for load balancer probes.

7. **QA** — run checklist in `docs/qa/2026-06-25-launch-readiness-qa.md` before go-live.

## Testing

No test infrastructure is configured. The `vitest`, `jest`, `playwright`, and `pytest` config references in `tsconfig.node.json` are boilerplate from the Vue project template — no actual test files or runners exist.

## Code Style

**Python server**: No linter/formatter configured. Follow standard Python conventions. Comments are in Chinese.

**Frontend**: No ESLint/Prettier configured for the Vue app.

## Environment

Server requires `.env` at `server/.env` with: DATABASE_URL, SECRET_KEY, MINIO_*, DEEPSEEK_API_KEY/MODEL, AI_DATABASE_URL, BOCHA_SEARCH_URL/API_KEY, ALIPAY_*, EMAIL_*, CLICKHOUSE_*. Frontend uses `.env.development` / `.env.production` with VITE_MINIO_ENDPOINT and VITE_SOCKET_URL.

## Known Issues

- ClickHouse integration (`shared/clickhouse_client.py`) is a stub — analytics not implemented yet.
- Full ECDICT word list is not bundled; use `ECDICT_CSV_PATH` or the sample CSV under `server/data/`.

## Migration Notes

The backend was migrated from NestJS to Python FastAPI. Migration spec at `docs/superpowers/specs/`. The `server/` directory is the sole active backend.

**Leftover NestJS artifacts** (safe to ignore): Root `package.json` has a `prisma.seed` key (no `prisma/` directory exists). `server/.env` has Prisma-related comments at the top.

## Utility Scripts

- `clear_chat_history.py` (repo root) — Clears LangChain chat history from the `langchain` database for all 5 chat role types per user. Run interactively.

## Companion Files

- `CLAUDE.md` — Parallel instructions for Claude Code agents, mirrors this file with minor differences.
- `docs/superpowers/plans/` and `docs/superpowers/specs/` — Feature plans and migration specs.
- `.mcp.json` — MCP server configuration (pencil tool).
