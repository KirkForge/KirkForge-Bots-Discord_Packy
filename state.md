# State — KirkForge-Bots-Discord_Packy (Gargoyle Packy V2)

*Tracked. Updated at session close. What changed, what's pending, what's blocked.*

## Current state
- Head: `<fill in at session close>`
- Tests: `<fill in at session close>`
- Last updated: 2026-07-21

---

# state.md — KirkForge-Bots-Discord_Packy (local, gitignored → now tracked)

Gargoyle Packy V2.0.0 — Discord character bot (Node/discord.js) + Python FastAPI
cognition microservice + commercial license/sales/update scaffold. Branch `dev`.

## Current state (uncommitted, 2026-07-17)
- **Direct LLM mode removed (ADR-010, uncommitted).** `src/bot/api/claudeAdapter.js`
  and `minimaxAdapter.js` deleted (staged D); `test/test_adapters.js` deleted.
  `callDirect` removed from `index.js`; `BOT_MODE=direct` branch removed from
  `core.js` and the message handler. Python `/respond` is the single LLM path.
  `BOT_MODE`/`PRIMARY_ADAPTER` retained as cosmetic `/status` fields.
- ADR-007 "out of scope" lie corrected; ADR-009 through ADR-015 added (license,
  sales, update, multi-character, radio, personal-assistant services). README +
  CHANGELOG synced.
- `packy_endpoint.py`: `PACKY_DEV_LICENSE=1` dev-bypass boots a community-tier
  pseudo-license (no signature) so a clean clone starts. `license/keys.py`
  ships a real 32-byte Ed25519 dev key (NOT all-zeros) — clean clone boots in
  dev. Production still bricks without a signed file.
- CI `.github/workflows/ci.yml`: node-version bumped 20 → 24 (both jobs, uncommitted).
- **Finding: `data/lorebook/packy_lorebook_structured.json.bak` (96KB) is a new
  untracked file. Not gitignored. Never committed (no history). Should be
  deleted or `*.bak` added to .gitignore — backup files must not be tracked.
- **Finding: `data/guild_config.json` new untracked — contains only test guild
  keys (test-guild-set/merge/deny/roundtrip), no secrets. OK but should be
  gitignored (runtime data) or seeded as a fixture.
- Cognition engine theater persists: `packy_cog_engine.py` still uses
  `random.choice` mad-libs (lines 238-305+). Unchanged. Not an LLM.
- Dead code still present: `small_orchestrator.py`, `packy_entry_ref.py`,
  `src/bot/packy.js`. Three snark files still separate (ADR-006 unfulfilled).
- CI still runs no pytest. `tests/test_{license,sales,update,admin}.py` and
  `test/test_{cognition,services}.py` unrun by CI.

## Remaining (prioritized)
1. Remove the .bak file (or gitignore `*.bak`).
2. Add a pytest job to CI — the valuable productization tests never run.
3. Delete `small_orchestrator.py`, `packy_entry_ref.py`, `packy.js`.
4. Consolidate the three snark files (ADR-006, still deferred).
5. Replace JSON-file persistence with a real DB.
6. Add metrics/Sentry — `logger.emit('alert')` still a stub.

## Direction source
No tracked state.md (this is local/gitignored). Durable source: README, CHANGELOG,
docs/ADR.md. ADRs 1-15 now cover the commercial scaffolding (was ADR-absent).