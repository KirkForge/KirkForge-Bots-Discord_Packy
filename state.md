# State — KirkForge-Bots-Discord_Packy (2026-07-22)

## What shipped this session (workorder-2026-07-22)

All 6 tasks completed:

### T4 — Chaos layer hardening + ADR-008 honesty (commit `77a8a7c`)
- Removed `mutation_flag` and `sabotage_flag` from `createChaosState()` (descoped per ADR-008)
- Removed `shouldSabotage()` function (descoped module 5, never called externally)
- Cleaned stale `mutation_flag`/`sabotage_flag` refs from `docs/MINIMAX_PROMPTS.md`
- Added `test/integration/chaos.test.js`: 18 assertions (chaos score ordering, cooldown, mood integration)
- Added chaos.test.js to `test:integration` script in package.json
- Gate: `npm run test:all` all pass, `grep mutation_flag src/bot/` → 0

### T1 — JS-side SQLite persistence (commit `0e41bab`)
- Added `src/bot/db.js`: thin SQLite wrapper using `node:sqlite` (Node 22+ DatabaseSync) with `better-sqlite3` fallback
- Rewrote `guildConfig.js`, `userState.js`, `chaosStatePersist.js` to use SQLite
- One-shot JSON→SQLite migration on first boot (marker file `.migrated_sqlite`)
- Added `PACKY_DB_PATH` env var to `.env.example`
- Added `test/integration/db.test.js`: 24 assertions (round-trips, WAL mode, migration, idempotent migration)
- Updated `guildConfig.test.js` to use `setGuildConfig` (was mutating returned objects, a semantic change)
- Original JSON files preserved as backup (never deleted)
- Gate: `npm run test:all` all pass

### T6 — Wire integration tests into CI (commit `bbdfb37`)
- Changed CI smoke job to `npm run test:all` instead of `node test/smoke.js`
- Changed `test:integration` script to glob pattern (adding new suites auto-picked up)
- Updated AGENTS.md §4 gates to reflect glob pattern

### T2 — Metrics + Sentry transport (commit `8ce9ddf`)
- Added `src/bot/metrics.js`: counter, gauge, timing, error interface
- Ring buffer (100-error cap) flushed to `data/metrics.json` every 60s
- Lazy-init Sentry from `SENTRY_DSN` (clean-clone safe without it)
- Wrapped 9 `logger.error` sites in `index.js` with `metrics.error()`
- Added per-command counters in `core.js` and `system.js`
- Added `/respond` latency timing in message handler
- Added `SENTRY_DSN` to `.env.example`
- Added `test/integration/metrics.test.js`: 12 assertions
- Gate: all pass

### T3 — Real LLM-backed response composer (commit `8d04819`)
- Removed composer from LLM prompt path (it was prepending mad-libs to the system prompt)
- Composer is now emergency fallback only (ADR-018)
- Chain: LLM primary → composer emergency fallback → "circuits fried" error
- Updated `packy_cog_engine.py` docstrings to honestly label as emergency fallback
- Added `tests/test_compose_fallback.py`: 10 assertions (think, interpret, docstrings)
- Added `PACKY_COMPOSE_MODEL` env (reserved for future cheaper-model fallback)
- Decision recorded: composer→prompt was the call graph, not composer→fallback

### T5 — AGENTS.md + ADR backfill (commit `8321827`)
- Added ADR-016 (JS-side SQLite), ADR-017 (Metrics/Sentry), ADR-018 (Composer emergency fallback)
- Fixed AGENTS.md stale refs: removed deleted-file quirks (packy_entry_ref.py, small_orchestrator.py, packy.js, claudeAdapter.js, minimaxAdapter.js)
- Updated Key Architecture tree to reflect single-LLM path and new modules (db.js, metrics.js)
- Updated dead-code note (ADR-006 Fulfilled, not deferred)

## Current HEAD

`8321827` on branch `workorder-2026-07-22` (7 commits ahead of `origin/dev`)

## What's pending

- Push `workorder-2026-07-22` branch to origin (needs merge/review before landing on dev)
- `@sentry/node` not yet added to package.json (it's lazy-loaded; works without it via ring buffer)
- `PACKY_COMPOSE_MODEL` env var is reserved but not yet wired to a cheaper model (T3 future work)
- ADR-008 chaos modules 3-5 remain descoped (separate ADR amendment task if revisited)

## Gate evidence

All tasks green-gated with:
- `npm run test:all` → 15 smoke + 19/19 rateLimiter + 18/18 guildConfig + 18/18 chaos + 24/24 db + 12/12 metrics
- `PYTHONPATH=. python3 -m pytest -q` → 76 passed
- `npm run lint` → exit 0
- `ruff check .` → "All checks passed!"
- `ruff format --check .` → "112 files already formatted"