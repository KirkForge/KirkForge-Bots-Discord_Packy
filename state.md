# State — KirkForge-Bots-Discord_Packy (2026-07-23)

## What shipped this session (workorder-2026-07-23)

All 4 tasks completed:

### T1 — FF main to dev (commit `5f4c1f9..8321827`)
- Merged dev → main via fast-forward (6 commits from prior workorder)
- Pushed to origin/main
- Gate: `git log --oneline -1 main` = `8321827`

### T2 — Response composer: real LLM fallback (commit `adbf249`)
- `PackyCogEngine.__init__` now accepts `llm_fn` parameter (constructor-injected from packy_endpoint)
- `think()` is now async: tries `_llm_fallback()` first (calls cheap LLM), falls back to `random.choice` templates
- `_llm_fallback()` calls injected `llm_fn` with `PACKY_COMPOSE_MODEL` (default: claude-haiku-4-5-20251001)
- `packy_endpoint.py`: added `_compose_llm_fn` wrapper that calls `_call_claude` directly (raises on failure)
- `call_llm`/`_call_claude` accept `model` override parameter
- Updated ADR-018: "emergency-only, random.choice" → "cheap-LLM fallback, random.choice last-resort"
- Added 5 LLM fallback tests + 2 docstring tests (15 total compose tests, up from 10)
- Updated `test_cognition.py` for async `think()`
- Gate: 81 Python tests passed, ruff check/format green

### T3 — Replace remaining JSON-file persistence with SQLite (commit `16ca92a`)
- `metrics.js`: replaced `fs.writeFileSync` flush to `data/metrics.json` with `flushMetricsToDb()` (SQLite)
- `loreSelector.js`: replaced `fs.readFile` with `readJsonFileAsync()` from db.js
- `db.js`: added `readJsonFile`, `readJsonFileAsync`, `flushMetricsToDb` utilities
- `db.js`: `resetForTesting` handles missing `metrics` table gracefully
- Gate: `grep "fs.readFile|fs.writeFile" src/bot/ src/cognition/` → only in db.js migration code

### T4 — Sentry integration in production (commit `e162352`)
- Added `@sentry/node ^9.0.0` to package.json dependencies
- Fixed `metrics.js`: `require('@sentry/node')` now uses `createRequire` (ESM compatibility)
- Added Sentry lazy-init smoke test: verify `error()` works with `SENTRY_DSN` set
- Updated `.env.example`: corrected metrics flush description (SQLite, not JSON)
- Gate: `npm run test:all` all pass (15/15 metrics, 30/30 db, 19/19 smoke, etc.), lint green

## Current HEAD

`e162352` on branch `workorder-2026-07-23` (3 commits ahead of `dev`)

## What's pending

- Push `workorder-2026-07-23` branch to origin (needs merge to dev)
- FF main to dev after merge (minor follow-up)
- Python side `packy_memory.py` still uses JSON file persistence (not in scope for this workorder, but noted for future)
- `PACKY_COMPOSE_MODEL` is now wired and active; consider adding a model override test that verifies the compose model is actually different from the primary model

## Gate evidence

All tasks green-gated with:
- `PYTHONPATH=. python3 -m pytest -q` → 81 passed
- `npm run test:all` → 19/19 smoke + 18/18 rateLimiter + 18/18 guildConfig + 18/18 chaos + 30/30 db + 15/15 metrics
- `npm run lint` → exit 0
- `ruff check .` → "All checks passed!"
- `ruff format --check .` → "112 files already formatted"