# Changelog — Gargoyle Packy

## [2.3.0] — 2026-07-23

### Security
- **T1**: Removed committed `.env` from git (already gitignored). Auth now required at startup: `PACKY_API_SECRET` must be set, or `PACKY_DEV_LICENSE=1` for local dev. Updated `.env.example` with missing vars and descriptive placeholder.

### Testing
- **T2**: Migrated Node tests from custom `console.log` runner to Vitest. 77 assertions across 6 test files with `describe/it/expect`. Added new assertions for rate limiter status tracking, chaos score bounds, concurrent DB writes, and metric aggregation.

### Dependencies
- **T3**: Added `stripe>=10.0` to pyproject.toml and requirements.txt. Unified Python dependency management: pyproject.toml is now the single source of truth. Removed requirements.txt. Updated CI and Dockerfile.cognition to use `pip install -e ".[dev]"`.

### CI
- **T4**: Added Python coverage (40% gate), mypy (`--exit-zero` first pass), TypeScript type checking (`tsc --noEmit` with `@ts-nocheck` on existing JS files), and Prettier formatting enforcement to CI. Updated tsconfig.json from `{}` to real config.

### Cleanup
- **T5**: Removed unused `@anthropic-ai/sdk` dependency. Added Prettier with `.prettierrc` config and format scripts. Fixed CI to cover `dev` branch PRs.

## [2.2.0] — 2026-07-23

### Architecture
- **T1**: FF main to dev (6 commits from workorder-2026-07-22 landed on main).
- **T2**: Cheap-LLM fallback wired into composer (ADR-018 updated). `PackyCogEngine.think()` now async; tries cheap LLM first, falls back to `random.choice` templates. Constructor-injected `llm_fn` from `packy_endpoint.py`.
- **T3**: Remaining JSON-file persistence replaced with SQLite. `metrics.js` flushes to SQLite via `db.js`. `loreSelector.js` uses `readJsonFileAsync` from `db.js`. Gate: `grep "fs.readFile|fs.writeFile" src/bot/` → only in db.js.
- **T4**: `@sentry/node ^9.0.0` added to package.json. Fixed ESM `require()` in `metrics.js` with `createRequire`. Added Sentry lazy-init smoke test.

## [2.1.0] — 2026-07-22

### Architecture
- **T1**: JS-side persistence migrated from JSON files to SQLite (node:sqlite / better-sqlite3). One-shot migration with `.migrated_sqlite` marker. Original JSON files preserved.
- **T2**: Added metrics interface (`src/bot/metrics.js`) with ring buffer + Sentry lazy-init. Per-command counters and `/respond` latency timing.
- **T3**: Removed stochastic composer from LLM prompt path (ADR-018). Composer is now emergency fallback only.
- **T4**: Removed descoped `mutation_flag`/`sabotage_flag` from `createChaosState()`. Removed `shouldSabotage()`. Added chaos integration tests.
- **T5**: Backfilled ADR-016 (SQLite), ADR-017 (Metrics/Sentry), ADR-018 (Composer emergency fallback). Fixed AGENTS.md stale references.
- **T6**: CI smoke job now runs `npm run test:all` (smoke + integration). Integration test script uses glob pattern.

## [2.0.0] — 2026-04-07

### Architecture

- Dropped fine-tuned local LLM (TinyLlama LoRA via llama.cpp) — replaced with API adapter pattern
- Python cognition layer now drives Claude / MiniMax via system prompt engineering
- Discord bot (discord.js v14) replaces web terminal UI as primary user surface
- Dual-mode bot: `direct` (API calls from Node) or `microservice` (FastAPI Python service)

### New — Bot Layer (Node.js)

- `src/bot/index.js` — Discord client, message handler, slash commands, per-user rate limiting
- `src/bot/signals.js` — Live CPU load + OpenWeatherMap weather reading
- `src/bot/userState.js` — Per-user interaction tracking (turnCount, mood history, interactionCount)
- `src/bot/guildConfig.js` — Per-guild settings (prefix, channel whitelist, mute, chaos flags)
- `src/bot/commands/register.js` — Slash command registration (/packy, /mood, /lore, /war)
- `src/bot/api/claudeAdapter.js` — Claude API adapter with exponential backoff retry
- `src/bot/api/minimaxAdapter.js` — MiniMax API adapter with same interface
- `src/bot/character/state.js` — PackyState class (JS port of Python layer/state.py)
- `src/bot/character/mood.js` — computeSnark / computeMood (JS port)
- `src/bot/character/keywords.js` — extractKeywords (JS port)
- `src/bot/character/snarkBank.js` — 186 deduplicated snark lines across 5 categories
- `src/bot/character/systemPrompt.js` — buildSystemPrompt() + getResponseStyleLimit()
- `src/bot/character/loreSelector.js` — Keyword + mood scored lore injection
- `src/bot/character/chaosState.js` — Controlled Chaos Layer (ADR-008): unprovoked commentary, target lock, mood overrides, command sabotage

### New — Orchestration

- `src/orchestration/packy_endpoint.py` — FastAPI microservice: POST /respond, GET /health, GET /state, POST /lore
- Full pipeline: resolve_packy_state → PackyCogEngine.think → lore selection → metadata header → assembled prompt
- Port configurable via `COGNITION_PORT` env var (default 8765)

### Updated — Python Cognition Layer

- `src/cognition/packy_brain.py` — Fixed all import paths for new folder structure (`core.snark.*` → relative imports)
- `src/cognition/__init__.py` — Made imports defensive with try/except
- `src/cognition/packy_actions.py` — Fixed snark import path

### New — Deployment

- `docker-compose.yml` — Two-service stack (cognition + bot) with health checks
- `Dockerfile` / `Dockerfile.cognition` — Separate images for each service
- `ecosystem.config.cjs` — pm2 config for local non-Docker development
- `scripts/start.sh` / `scripts/stop.sh` — pm2 process management scripts
- `scripts/register_commands.sh` — Slash command registration helper
- `requirements.txt` — Python dependencies pinned

### New — Data

- `data/lorebook/new_lore_entries.json` — 20 new lore entries (hardware trauma, software wars, teaching moments, philosophy)

### New — Tests

- `test/test_cognition.py` — Python cognition layer smoke tests (6 tests)
- `test/test_endpoint.js` — FastAPI endpoint integration tests
- `test/test_adapters.js` — API adapter unit tests with mocks

### New — Docs

- `docs/ADR.md` — 15 Architecture Decision Records (001–008 original, 009–015 commercial + feature)
- `docs/PROJECT_OVERVIEW.md` — Full architecture map
- `docs/MINIMAX_PROMPTS.md` — 7 ready-to-use MiniMax prompts for content generation
- `LLM_readmap.md` — LLM-first context document for cold-start sessions
- `README.md` — Project documentation

### Removed / Archived

- LoRA checkpoints (checkpoint-10 through checkpoint-170) — not carried forward
- llama_adapter.py — archived to `docs/design/llama_adapter_ref.py`
- Web terminal UI (index.html, app.js, Flask routes) — deferred
- TTS engine, alarms, reminders, scheduler — original `python_core.*` zip artifacts not extracted verbatim; functionality re-implemented live in `src/cognition/services/` and mounted on the cognition service (see ADR-009)
- Google OAuth — original `google_oauth_cli.py` zip artifact not extracted; re-implemented live in `src/cognition/services/google/` (see ADR-009)

---

## [1.x] — 2025-12

*Original Packy — local LLM assistant running TinyLlama via llama.cpp on a Packard Bell laptop.*
*Sources archived in `/path/to/Packy/` zip files.*
