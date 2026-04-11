# CrowdSignal Backend

Django 4.2 + DRF backend for the CrowdSignal trading signals platform. Aggregates social sentiment from Reddit/StockTwits, computes trading signals, tracks accuracy, and powers a simulated portfolio.

**Status:** Backend MVP complete — 197 tests passing, 0 `manage.py check` errors, 20/20 planned tasks done.

---

## Tech Stack

- **Framework:** Django 4.2, Django REST Framework
- **Auth:** `rest_framework_simplejwt` (JWT) + `dj-rest-auth` + `django-allauth` (GitHub/Google OAuth)
- **Database:** PostgreSQL (prod), SQLite in-memory (tests)
- **Async:** Celery + Redis (broker + result backend)
- **Realtime:** Django Channels over Daphne (ASGI), Redis channel layer
- **Rate limiting:** `django-ratelimit`
- **Package manager:** `uv`
- **Python:** 3.14

---

## Implemented Features

### Authentication & Authorization
- [x] Custom `CustomUser` with `role` field (`user` / `admin`) and JSONField `permissions` (RBAC scaffold)
- [x] JWT access/refresh tokens (5 min / 7 days, rotating + blacklist)
- [x] OAuth login via GitHub and Google (`dj-rest-auth` + `allauth`)
- [x] `IsAdmin` and `HasPermission("scope")` permission classes
- [x] Rate limiting on auth endpoints (20/min per IP)
- [x] Global `IsAuthenticated` default on all API endpoints

### Core Domain
- [x] **Tickers** — CRUD, user-scoped **Watchlist** (M2M)
- [x] **Social posts** — Reddit + StockTwits fetchers, sentiment scoring, deduplication
- [x] **Signal engine** — sentiment/momentum/consistency, BUY/SELL/HOLD, aggregation fields, explanation endpoint
- [x] **Alerts** — auto-generated from signals, admin-only resolve
- [x] **Market data** — Alpaca stream integration, price snapshots, technical indicators (SMA, RSI)
- [x] **Pipeline** — coordinated fetch → score → signal → alert flow

### Portfolio & Trading
- [x] User-scoped `Portfolio` (OneToOne, auto-created with $100k starting cash)
- [x] Buy/Sell endpoints with `transaction.atomic()` + `select_for_update()` (concurrency-safe)
- [x] Position tracking with avg price, Trade history
- [x] Insufficient funds / over-sell validation

### Intelligence & Audit
- [x] **Signal accuracy tracking** — hourly Celery task evaluates predictions against 24h price movement
- [x] **Decision logging** — full audit trail of engine decisions (admin-only list/detail, filterable by ticker)
- [x] **Dream-feature scaffolds** with TODO stubs:
  - `apps/intelligence`: `MarketMoodSnapshot`, `ManipulationFlag`, `RetrainLog`
  - `apps/strategies`: `StrategyRule`, `RuleCondition`, `RuleAction`, `StrategyExecution` + full CRUD

### Data Export
- [x] `/api/export/ticker/{symbol}/` — CSV or JSON
- [x] Configurable includes: `posts,signals,prices,alerts`
- [x] Date filtering (`from`, `to` ISO 8601)
- [x] Streaming CSV response, 10,000 row cap
- [x] Rate limited (5/min per user)

### Event Bus
- [x] `apps/events` Redis pub/sub with `publish(event_type, payload)`
- [x] Graceful failure (logs, never crashes callers)
- [x] Event types: `SIGNAL_GENERATED`, `ACCURACY_EVALUATED`, `ALERT_CREATED`, `PRICE_UPDATED`, `PIPELINE_COMPLETED`
- [x] Wired into: signal engine, pipeline, alerts, accuracy task, price stream

### Testing & Quality
- [x] 197 tests passing (auth, permissions, trading, signals, alerts, pipeline, export, strategies, audit)
- [x] Shared fixtures in `conftest.py`: `user`, `admin_user`, `auth_client`, `admin_client`, `ticker`, `seeded_portfolio`
- [x] Test settings: SQLite `:memory:`, `InMemoryChannelLayer`, `LocMemCache`, `RATELIMIT_ENABLE=False`
- [x] `CELERY_TASK_ALWAYS_EAGER` in tests

---

## Project Layout

```
backend/
├── apps/
│   ├── accounts/       # CustomUser, permissions, OAuth views
│   ├── tickers/        # Ticker CRUD + Watchlist
│   ├── social/         # Reddit/StockTwits fetchers, SocialPost
│   ├── sentiment/      # Sentiment scoring pipeline
│   ├── signals/        # SignalEngine, SignalSnapshot, SignalAccuracy, DecisionLog, Alerts
│   ├── market/         # Alpaca stream, PriceSnapshot, indicators
│   ├── portfolio/      # Portfolio, Position, Trade (user-scoped, atomic)
│   ├── pipeline/       # Orchestration of fetch → signal → alert
│   ├── events/         # Redis pub/sub bus + event type constants
│   ├── export/         # Data export (CSV/JSON streaming)
│   ├── intelligence/   # Scaffolds: MarketMood, ManipulationFlag, RetrainLog
│   └── strategies/     # Scaffolds: StrategyRule + CRUD + engine stub
├── config/
│   ├── settings/
│   │   ├── base.py     # Shared settings
│   │   └── test.py     # SQLite + in-memory layers
│   ├── urls.py
│   └── asgi.py
├── conftest.py         # Shared pytest fixtures
└── pyproject.toml
```

---

## Running

### Prerequisites
- Docker + docker-compose (for Postgres + Redis), OR local Postgres/Redis
- Python 3.14, `uv`

### Quick Start
```bash
# From project root
docker-compose up -d db redis

# Backend
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

### Tests
```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test uv run python -m pytest
```

### Checks
```bash
DJANGO_SETTINGS_MODULE=config.settings.test uv run python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test uv run python manage.py makemigrations --check --dry-run
```

---

## Environment Variables

See `.env.example` at the project root. Key variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret |
| `POSTGRES_*` | DB connection |
| `CELERY_BROKER_URL` | Redis URL for Celery and event bus |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `ALPACA_API_KEY` / `ALPACA_API_SECRET` | Market data stream |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins |

---

## What's Left / Roadmap

### Must-have before v1 frontend launch
- [ ] **Frontend** — React/Vite client consuming these APIs (in `frontend/`, currently scaffolded)
- [ ] **OAuth callback URLs** — register GitHub + Google apps with real client IDs, update `.env`
- [ ] **Production settings** — `config/settings/production.py` with stricter CORS, secure cookies, logging
- [ ] **Email/verification flow** — `ACCOUNT_EMAIL_VERIFICATION = "none"` is MVP-only

### Dream features (scaffolded, need activation)
- [ ] **Intelligence layer** — fill in TODO stubs in `apps/intelligence/`:
  - Market mood computation from aggregate signals
  - Manipulation/anomaly detection (sudden sentiment spikes)
  - Model retraining logs and scheduling
- [ ] **Strategy agents engine** — execute `StrategyRule` against live signals, record `StrategyExecution`
- [ ] **API keys** — activate `APIKey` model: generation endpoint, auth backend, scope enforcement middleware

### Nice-to-have / Post-MVP
- [ ] **API documentation** — `drf-spectacular` for OpenAPI schema + Swagger UI
- [ ] **Observability** — structured logging, Sentry, Prometheus metrics on event bus
- [ ] **Signal engine ML path** — wire `prediction_method="ml"` branch (currently only `rule_based`)
- [ ] **Backtesting** — replay historical data through pipeline for strategy evaluation
- [ ] **Paper trading broker integration** — connect portfolio to Alpaca paper account
- [ ] **Websocket client auth** — JWT validation on Channels consumers
- [ ] **Celery beat schedule** — concrete hourly/daily schedule for accuracy eval and data fetches

### Known minor issues
- [ ] `apps/accounts/models.APIKey` — unused scaffold model, has migration; enforce or remove in v1
- [ ] JWT `SECRET_KEY` length warning in tests (29 bytes vs. recommended 32+) — pre-existing dev key
- [ ] Signal history endpoint capped at 100 records without pagination — consider cursor pagination
- [ ] Export endpoint uses `values()` dict slicing — acceptable for 10k cap, but no streaming DB cursor

---

## Architecture Notes

- **Monolith + event bus**: All domain code lives in `apps/*`, but cross-app communication goes through `apps.events.bus.publish()` rather than direct imports, keeping modules decoupled.
- **User isolation**: Portfolio, Watchlist, and StrategyRule are all user-scoped via `filter(user=request.user)`. Tests verify isolation explicitly.
- **Admin-only endpoints**: `DecisionLog`, `AlertResolve` use `[IsAuthenticated, IsAdmin]`.
- **Atomic trading**: Buy/Sell wrap DB writes in `transaction.atomic()` with `select_for_update()` locks on `Portfolio` and `Position`.
- **Graceful degradation**: Event bus catches all Redis errors and logs them — signal generation never fails because of pub/sub issues.
