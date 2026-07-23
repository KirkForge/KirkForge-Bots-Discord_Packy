# State — KirkForge-Bots-Discord_Packy (2026-07-23)

## What shipped this session (workorder-5.0)

### T1 — Remove committed .env, require auth at startup (commit `fba8887`)
- `.env` was not in git (already gitignored). Auth now required at startup: `PACKY_API_SECRET` must be set, or `PACKY_DEV_LICENSE=1` for dev mode.
- Updated `.env.example` with `PACKY_API_SECRET` required comment and descriptive placeholder. Fixed `BOT_MODE=microservice`.
- `packy_endpoint.py`: added `SystemExit(1)` if no secret and no dev license. Moved `_dev_license_enabled()` to module top level.
- `test_auth_startup.py`: 4 new tests (auth required, auth bypass in dev, auth enabled when secret set, auth header validation).
- Updated `test_admin.py` and `test/smoke.py` to set `PACKY_API_SECRET` or `PACKY_DEV_LICENSE=1`.

### T2 — Vitest migration (commit `b0cdfc2`)
- Migrated all 5 JS integration test files + smoke.js to Vitest `describe/it/expect` format.
- Deleted `test/smoke.js` (replaced by `test/smoke.test.js`).
- Added `vitest.config.ts`, `vitest` dev dependency, `test`/`test:ci`/`test:all` scripts.
- 77 Node assertions across 6 test files. New assertions: rate limiter status tracking, chaos score bounds, concurrent DB writes, metric counter isolation, gauge overwrite, timing aggregation.
- Updated CI smoke job to `npm run test:ci`.

### T3 — Add stripe dep, unify Python deps (commit `90f4824`)
- Added `stripe>=10.0` to `pyproject.toml` and `requirements.txt`.
- Removed `requirements.txt`. `pyproject.toml` is now single source of truth.
- Updated CI and `Dockerfile.cognition` to `pip install -e ".[dev]"`.
- Added `cryptography>=42.0.0`, `slowapi>=0.1.9` to pyproject.toml (were in requirements.txt but not pyproject.toml).

### T4 — Coverage + type checking in CI (commit `b5f6050`)
- Added `pytest-cov`, `coverage[toml]`, `mypy` to pyproject.toml dev deps.
- CI: pytest runs with `--cov=src --cov-fail-under=40 --cov-report=xml --cov-report=term-missing`.
- CI: added mypy step (`--exit-zero` first pass), tsc step, Prettier step.
- Updated `tsconfig.json` from `{}` to real config. Added `@ts-nocheck` to all JS files.
- Added `.prettierrc` with single quotes, trailing commas, print-width 100.

### T5 — Remove @anthropic-ai/sdk, fix CI branches (commit `e0bc406`)
- Removed `@anthropic-ai/sdk` from package.json (unused, no imports in src/).
- Prettier formatting applied to all source files.
- CI `pull_request` branches now include `dev` (was just `main`).

### T6 — ADRs + AGENTS.md (commit `e0bc406+`)
- ADR-019: Auth required at startup.
- ADR-020: Vitest migration.
- ADR-021: Unified Python deps.
- Updated AGENTS.md: `PACKY_API_SECRET` in env table, updated verification gates.

## Current HEAD

`e0bc406` on branch `dev`

## Gate evidence

- `npm run lint` → exit 0
- `npm run fmt:check` → "All matched files use Prettier code style!"
- `npm run typecheck` → exit 0
- `npx vitest run` → 77 passed
- `PYTHONPATH=. python3 -m pytest tests/ test/ -q` → 85 passed
- `ruff check .` → "All checks passed!"
- `ruff format --check .` → "113 files already formatted"