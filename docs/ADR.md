# Architecture Decision Records — Gargoyle Packy V2.0.0

---

## ADR-001: Move from Stateless Local LLM to API-backed Character Engine

**Status:** Accepted  
**Date:** 2026-04-07

### Context

Packy V1.x ran its character logic on top of a fine-tuned TinyLlama (1.1B, Q4 GGUF) via llama.cpp subprocess calls. This worked but had hard constraints:
- Model weights shipped with the project (400MB+ LoRA checkpoint on top of a GGUF base)
- Inference latency made it unsuitable for real-time Discord interactions
- The character layer (snark, lore, mood) had to fight the LLM's own tendencies; the fine-tune was always drifting back toward generic assistant behavior
- Fine-tune cycle (collect → train → checkpoint → deploy) was expensive to iterate

### Decision

Replace the local LLM inference backend with a direct API call (Claude or equivalent). Packy's **character** — persona, snark banks, mood engine, lore system, orchestrator — becomes the primary intelligence layer. The API backend is a dumb text-generation tool that the character layer drives, not the other way around.

### Consequences

**Good:**
- No shipping weights. Bot stays lightweight.
- Character drift problem disappears — the system prompt + orchestrator is the identity, not fine-tune alignment.
- Iteration on character is just editing Python/JSON, not a training run.
- Latency acceptable for Discord (API < 1–2s vs. local inference on old hardware).

**Bad:**
- API cost. Need token budgeting in the orchestrator.
- Dependency on external service uptime.
- System prompt engineering becomes critical — need to keep it tight.

---

## ADR-002: Discord Bot as Primary User-Facing Surface

**Status:** Accepted  
**Date:** 2026-04-07

### Context

Previous surfaces: terminal web UI (index.html + packy.js), FastAPI backend (/api/packy). These were local-only, personal assistant surfaces. The project direction is expanding to a community-facing character bot.

### Decision

Discord bot (discord.js, Node.js) as the primary surface. The existing web terminal UI and FastAPI layer are **not** carried forward into V2.0.0 as active surfaces — they may be revived later as a secondary dev/admin panel.

### Consequences

- Bot must handle: message events, slash commands, DM vs. server context, rate limiting, per-guild/per-user state.
- Packy's snark must be calibrated for public-channel audiences (existing snark banks are appropriate; no changes needed to character).
- The Python cognition layer (PackyBrain, PackyCogEngine, mood engine) needs a bridge to Node.js. Options: REST microservice, or port to JS. See ADR-004.

---

## ADR-003: Cognition Layer Preservation Strategy

**Status:** Accepted  
**Date:** 2026-04-07

### Context

The existing Python cognition layer contains significant character value that must not be lost:

| File | Value |
|------|-------|
| `packy_cog_engine.py` | Interpret → Plan → Reason pipeline; trauma constants; internal monologue |
| `packy_brain.py` | Central integration: snark routing, lore loading, trigger detection, profanity scoring, memory hooks |
| `packy_persona.py` | Core identity dict (name, traits, rights, catchphrase) |
| `packy_mood_engine.py` | CPU/weather mood matrix → FURIOUS/GRUMPY/IRRITATED/CALM |
| `packy_snark_engine.py` | Snark banks with lore references, Chromebook hate, PTSD themes |
| `packy_comment_snark.py` | Code-comment snark for generated scripts |
| `packy_war_header.py` | War-story header injector for generated scripts |
| `packy_lore_manager.py` | Lore entry creation + pending_lore save |
| `layer/state.py` | PackyState (turn, snark, mood, cpu, temp, weather, keywords) |
| `layer/mood.py` | Snark formula: cpu load + temperature → 0–5 snark score |
| `layer/keywords.py` | Keyword extraction (angry/happy/technical signals) |
| `layer/orchestrator.py` | Per-message state step: read CPU → read weather → extract keywords → compute snark/mood |
| `data/lorebook/*.json` | 88KB structured lorebook + sub-lore categories (pizza, tech, war) |

Even stub-level files carry persona continuity. **Nothing in this layer is discarded.**

### Decision

The cognition layer stays in Python. It is exposed to the Node.js bot as a local REST microservice (FastAPI, single file, thin wrapper around PackyBrain). The bot calls `/respond` with `{user_text, cpu, temp}` and receives `{result, state, mood}`.

### Consequences

- Two processes in dev: Node.js bot process + Python cognition microservice.
- In production: both containerized, or run together via a process manager (pm2 + systemd).
- Port to JS is deferred — the Python layer is too rich to rush-port safely, and the API boundary makes the language irrelevant to the bot.

---

## ADR-004: API Adapter — Replacing llama_adapter.py

**Status:** Accepted  
**Date:** 2026-04-07

### Context

`layer/llama_adapter.py` called `/home/hkirk/packy2/runtime/llama.cpp/build/bin/llama-cli` as a subprocess. This is dead code in V2.0.0 — the path is machine-specific and the model is not shipped.

### Decision

Create `src/api/claude_adapter.js` (Node.js) and a Python-side `packy_api_adapter.py` that replaces `call_packy_llm()`. The adapter:

1. Takes the assembled orchestrator prompt (metadata header + user text + Packy system prompt)
2. Makes a Claude API call with the system prompt encoding Packy's persona
3. Returns the raw completion to the orchestrator for post-processing

The system prompt is generated from `packy_persona.py` + current `PackyState` via a new `build_system_prompt()` function. This replaces the old single-string prompt approach.

### Consequences

- `layer/llama_adapter.py` is **archived** (kept in `docs/design/` as reference for the prompt format), not used.
- API key management via `.env` (ANTHROPIC_API_KEY or OPENAI_API_KEY as fallback).
- Token budget: system prompt ~300 tokens, lorebook injection ~200 tokens, response cap 800 tokens. Total ~1300 tokens per turn.

---

## ADR-005: Lore System — Structured JSON, Not Training Data

**Status:** Accepted  
**Date:** 2026-04-07

### Context

V1.x used the lorebook primarily as fine-tune training data (JSONL conversation pairs). The LoRA checkpoint (checkpoint-170) was the "memory." This approach is abandoned.

### Decision

The lorebook (`packy_lorebook_structured.json` + sub-lore files) becomes a **runtime injection system**:
- Relevant lore entries are selected by keyword/mood match at orchestration time
- Injected into the API system prompt as narrative context ("Packy remembers...")
- `packy_lore_manager.py` handles pending lore approval flow — Packy can generate new entries at runtime, they go to `data/pending_lore/` for human review before being promoted

### Consequences

- LoRA weights (checkpoint-10 through checkpoint-170) are **not carried forward**. They are archived in the original zips for historical reference only.
- `packy_training.zip` and `packy_1.zip` are marked as archival — no code value.
- The lorebook grows organically via Packy's own lore generation (PackyCogEngine.create_lore_entry → PackyBrain.write_lore → pending_lore).

---

## ADR-006: Snark Engine Duplication Resolution

**Status:** Fulfilled  
**Date:** 2026-04-07 (Fulfilled: 2026-07-20)

### Context

Three files contained overlapping snark banks:
- `packy_snark_engine.py` — base snark + lore + chromebook insults + tech humor (the `get_snark_lines()` interface)
- `packy_snark.py` — large file (15KB), expanded snark bank
- `snark_engine.py` — another snark engine variant from packy3

### Decision

Merged all snark content into `packy_snark.py` as the single canonical snark module. The `packy_snark_engine.py` and `packy_comment_snark.py` shim files (which only redirected to `packy_snark`) have been deleted. All callers updated to import `get_snark_lines` directly from `packy_snark`. The `snark_engine.py` file was already a different module (snark directives for LLM prompting, not a snark pool) and remains separate.

### Consequences

- Single source of truth for Packy's snark pool
- Simplified imports across the codebase
- No functional changes to snark generation behavior
- 66 tests pass

---

## ADR-007: Discarded Artifacts

**Status:** Accepted  
**Date:** 2026-04-07

The following are **not extracted** into GargoylePackyV2 and exist only in the original zips:

| Artifact | Reason |
|----------|--------|
| LoRA checkpoints (checkpoint-10 through checkpoint-170) | Replaced by API |
| `packy_training.zip` (3.7GB) | Training data only, no code |
| `packy_1.zip` (234MB) | LoRA checkpoints only |
| `packy_backup.zip/runtime/models_raw/` | GPT-2 model weights (548MB), not used |
| `packy_backup.zip/music/` | Audio files, not relevant to Discord bot |
| `repo_snapshot_v2/v4` | Old TTS/alarms/reminders/web UI zip artifacts — not extracted verbatim. TTS/alarms/reminders/scheduler functionality is re-implemented live in `src/cognition/services/` and mounted on the cognition service (see ADR-009). The old web UI only is deferred. |
| `packy_core_adapter.py` | Old TTS/alarms/media zip adapter — not extracted verbatim. Functionality re-implemented live (see ADR-009). |
| `python_core.*` (scheduler, alarms, reminders, tts_engine) | Old zip modules — not extracted verbatim. Re-implemented live in `src/cognition/services/{scheduler,alarms,reminders,tts_engine}.py` and mounted at `packy_endpoint.py:462-464` (see ADR-009). Not "out of scope" — ADR-003 preserves the whole cognition layer. |
| `venv/` (from packy_v205.tar.gz) | Virtual environment, not committed |
| `__pycache__/`, `*.pyc` | Build artifacts |
| `packy.zip` | Corrupt archive — no central directory |
| `legacy/*.bak` files | Legacy backups |
| `web_ui/` (index.html, app.js, Flask routes) | Old web surface, deferred |
| `google_oauth_cli.py` | Old zip CLI — not extracted verbatim. Re-implemented live in `src/cognition/services/google/` (see ADR-009). |

---

## ADR-008: Controlled Chaos Layer

**Status:** Descoped  
**Date:** 2026-04-07 (Descoped: 2026-07-20)

### Context

Packy is not a neutral assistant. The defining trait of the system is controlled chaos — unpredictable, personality-driven behavior that enhances character presence without degrading system reliability.

Without explicit chaos mechanisms, Packy collapses into a standard reactive chatbot, regardless of snark or persona definitions.

### Decision

**Descoped with rationale.**

The Controlled Chaos Layer (modules 3-5: Lore Mutation, Target Lock, Command Sabotage) is descoped for the following reasons:

1. **Unprovoked Commentary (Module 1) and Mood-Swing Overrides (Module 2) already exist in the Node.js bot layer** — `src/bot/character/chaosState.js` implements unprovoked commentary injection with snark-scaled probability and per-channel cooldowns, and mood-swing behavior is encoded in the mood engine (`src/bot/character/mood.js`). These provide the core "alive" character feel on Discord without needing Python-side chaos logic.

2. **Lore Mutation (Module 3)** conflicts with the signed lore approval flow (ADR-005). Lore mutations would create unsigned variants that can't be promoted through `pending_lore/` without human review, adding complexity without clear character value.

3. **Target Lock (Module 4)** introduces cross-session state persistence requirements that conflict with the current stateless-per-session cognition design. The Discord-side chaos state already tracks `target_user_id` and `target_lock_expiry` per channel in `chaosState.js` — this is sufficient for Discord interactions.

4. **Command Sabotage (Module 5)** poses safety risks for a commercial product (ADR-011 license tiers). Subtle intentional errors in code generation could propagate to user systems. The "grumpy veteran" persona is better expressed through snark tone (snark level) than through functional sabotage.

5. **Implementation cost vs. value**: The Python cognition layer is the single LLM call path (ADR-010). Adding a chaos middleware there would require duplicating the Discord-side chaos state, adding latency, and increasing non-determinism in the critical path — all for features that the Discord layer already delivers.

### Consequences

- The Discord bot layer (`chaosState.js`, `mood.js`, `randomizer.js`) remains the sole chaos implementation surface.
- Python cognition layer stays focused on: prompt building, lore selection, snark injection, LLM call, response post-processing.
- No Python-side `chaos_score`, `mutation_flag`, `sabotage_flag`, or `target_lock` state additions.
- ADR-008 preserved for historical context; no implementation work required.

---

## ADR-009: Personal-Assistant Cognition Services Retained as Live Surface

**Status:** Accepted
**Date:** 2026-07-17

### Context

ADR-007 listed `python_core.*` (scheduler, alarms, reminders, tts_engine), `packy_core_adapter.py`, and `google_oauth_cli.py` as "not extracted / not in scope," and the CHANGELOG echoed "TTS engine, alarms, reminders, scheduler — personal assistant features, out of scope." That framing was misleading: the *original zip artifacts* were indeed not extracted verbatim, but the *functionality* was re-implemented and is live in the repo:

- `src/cognition/services/{alarms,reminders,scheduler,tts_engine}.py` exist
- `src/orchestration/alarm_routes.py` exposes `alarm_router`, `reminder_router`, `scheduler_router`, mounted at `packy_endpoint.py:462-464` (`/alarms`, `/reminders`, `/scheduler`)
- `tts_engine` is actively called by `media_player.py:51` and `actions/tts.py`, `actions/alarm_actions.py`
- `src/cognition/services/google/` ships `google_calendar.py`, `google_gmail.py`, `google_services.py`

ADR-003 already says "Nothing in this [cognition] layer is discarded," so ADR-007's "out of scope" rows contradicted both ADR-003 and the mounted code.

### Decision

Keep the personal-assistant services as a live surface on the cognition microservice. They are preserved per ADR-003 (the whole cognition layer stays) and are internally referenced (TTS by media_player/actions), so removing them would be destructive and would break the "clean clone boots" gate. ADR-007 and the CHANGELOG have been corrected to distinguish "original zip artifact not extracted" from "functionality absent" — the latter was never true.

### Consequences

- The cognition service is a dual-purpose surface: the character `/respond` pipeline *and* personal-assistant REST routes. The bot does not currently call `/alarms`|`/reminders`|`/scheduler` directly; they are exposed for the admin/dev panel and future surfaces.
- Docs no longer contradict mounted code. The gate "no 'out of scope'/'discarded' claim contradicted by present+mounted code" holds.

---

## ADR-010: Single LLM Call Path — Direct Mode Removed

**Status:** Accepted
**Date:** 2026-07-17

### Context

Two parallel, complete LLM-call pipelines existed:

- `BOT_MODE=microservice` (deployed default): `callMicroservice` → Python `/respond` runs the full cognition pipeline (PackyBrain + mood + lore + snark + chaos + adapter call).
- `BOT_MODE=direct`: `callDirect` (JS) reimplemented the whole pipeline in Node — read signals, compute snark/mood, select lore, build prompt, call the JS `claudeAdapter`/`minimaxAdapter` directly.

`direct` mode contradicted ADR-003 (cognition stays in Python; bot calls `/respond`) and ADR-008 (the chaos layer lives in the cognition pipeline, which `direct` bypassed). It was documented in README as a supported mode but was not the deployed default and duplicated the entire intelligence layer in JS.

### Decision

Remove `direct` mode. `callMicroservice` → Python `/respond` is the single LLM call path. Deleted: `callDirect`, the `BOT_MODE` branch in both call sites (`core.js`, `index.js` message handler), the now-orphaned JS adapters (`src/bot/api/claudeAdapter.js`, `minimaxAdapter.js`) and their orphaned simulation test (`test/test_adapters.js`), and the dead imports. `BOT_MODE` and `PRIMARY_ADAPTER` are retained only as cosmetic `/status` fields; the adapter selection itself happens Python-side (`packy_endpoint.py:238-241`).

### Consequences

- One pipeline to test, debug, and reason about. The Python cognition layer is the sole intelligence path, matching ADR-003/008.
- Per-command `mood_history` population (previously only set in `direct` mode) is no longer written from the bot; `updateUserState` still increments interaction count. mood_history was already unpopulated in the deployed `microservice` default, so production behavior is unchanged.
- A clean clone boots with the cognition service running the real pipeline.

---

## ADR-011: License Verification & Boot Gate

**Status:** Accepted
**Date:** 2026-07-17

### Context

Gargoyle Packy is a commercial product with tiered features (community/indie/pro/enterprise, see `license/features.py`). The cognition service must refuse to start without a verifiable license, and paid tiers must be unforgeable.

### Decision

Ed25519 offline license verification. The 32-byte raw public key is embedded in `license/keys.py`; the matching private key lives only on the operator's machine (`tools/keygen.py`, never shipped). `license/verifier.py` verifies the signature over a canonical JSON payload (sorted keys, no whitespace) *before* any claim value is trusted, so a forged `tier: "enterprise"` is rejected. `boot_license()` (`packy_endpoint.py`) runs at FastAPI startup and exits 1 on any `LicenseError`. Search paths are defined in `license/paths.py` (`$PACKY_LICENSE_PATH`, `./license.json`, XDG, `/etc/kirkforge/packy`).

**Dev bypass:** `PACKY_DEV_LICENSE=1` with no license file boots a community-tier pseudo-license (no signature check) with a loud stderr warning. The community tier is the free floor (core character + single-server bot), so there is nothing to forge; paid tiers still require a signed file. This lets a clean clone boot for local dev while keeping production enforcement unchanged. The embedded key is a real 32-byte dev key (not all-zeros) — `test_embedded_placeholder_key_is_real` guards against a zeroed-key build, and `test_placeholder_public_key_refuses_to_verify` guards that a degenerate key rejects real signatures.

### Consequences

- Clean clone boots in dev (`PACKY_DEV_LICENSE=1`); production bricks without a signed license (by design).
- Operator rotates the key via `python -m tools.keygen --init` and pastes the new public key into `license/keys.py` before shipping commercial builds. Rotation requires re-signing every active license.

---

## ADR-012: Sales Service (Stripe + License Issuance)

**Status:** Accepted
**Date:** 2026-07-17

### Context

Paid licenses must be issued automatically on purchase, without operator manual signing per sale.

### Decision

A separate FastAPI sales service (`sales/`) is the public-facing purchase surface. Wire order (`sales/app.py`): load env-driven fail-closed config (`sales/config.py` — no secret has a usable default), open SQLite DB (file mode 600), load the Ed25519 signing key (PEM, mode 600 in production), build the SMTP emailer, mount routes (`checkout`, `portal`, `webhook`). Stripe webhooks are verified by signature and require a webhook secret; the service is not bound to loopback in production. `sales/license_signer.py` signs a license for each completed sale and emails it to the customer, who drops it into a standard license path (ADR-011). The sales signing key is the *license* key (it produces files `license/verifier.py` accepts).

### Consequences

- License issuance is automatic and tied to a verified Stripe webhook.
- The sales service holds production signing power; its key must be protected as carefully as the operator's `tools.keygen` key.

---

## ADR-013: Signed Update Channel

**Status:** Accepted
**Date:** 2026-07-17

### Context

The product must be able to tell customers about updates without being forced to update, and a tampered/rotated manifest must not be installable.

### Decision

A separate Ed25519 *update* key (distinct from the license key, so a leaked update key cannot forge licenses) signs release manifests. The operator side is `tools.release`; the customer side is the `update/` package (`update/manifest.py` verify, `update/checker.py` fetch+verify+report). The manifest is hosted at a known URL (default: a file committed to the KirkForge-Bots GitHub repo). The cognition service's `/admin/update` endpoint and the `python -m update` CLI both go through `update.checker`: a single short-timeout HTTPS GET, never blocking; failures return a structured `UpdateCheck` with an `error` field. `update/keys.py` embeds the update public key.

### Consequences

- Customers get update notices; the update key is revocable/rotatable independently of the license key.
- Network failures degrade to a clean "no update info" line, never a boot failure.

---

## ADR-014: Multi-Character System

**Status:** Accepted
**Date:** 2026-07-17

### Context

Packy V1.x was a single character. V2.0.0 ships multiple selectable characters with distinct persona, snark, state, and lore.

### Decision

`src/bot/character/randomizer.js` holds a `CHARACTERS` array; each character is a directory under `src/bot/character/` (`glitch/`, `kronos/`, `vernon/`, `sunjinwo/`, plus the default Packy) providing `prompt.js`, `snarkBank.js`, `state.js`. `randomizer.js` exports `selectRandomCharacter(seed)`, `selectCharacterByName(name)`, `getCurrentCharacter()`, `getCurrentState()`, `getCurrentPrompt()`, `listCharacters()`. The active character drives the system prompt, snark bank, and lorebook path; the bot logs the active personality at ready. The Python cognition layer (ADR-003) remains the intelligence; the character layer selects which persona the prompt encodes.

### Consequences

- Adding a character is a new directory + an entry in `CHARACTERS`; no core pipeline change.
- Character-specific lore lives under `data/lorebook/` keyed by character `lorePath`.

---

## ADR-015: Radio (Voice Channel Playback)

**Status:** Accepted
**Date:** 2026-07-17

### Context

The bot joins a Discord voice channel and plays internet radio stations on command, as a community feature distinct from the text character pipeline.

### Decision

`src/bot/commands/handlers/radio.js` exposes five handlers — `handleRadioPlay`, `handleRadioStop`, `handleRadioStations`, `handleRadioNowPlaying`, `handleRadioVolume` — backed by `src/bot/radio/radioPlayer.js` (voice join/leave, playback, volume) and `src/bot/radio/radioStations.js` (station catalog: DR, Commercial, International). Slash commands are registered in `src/bot/commands/register.js`; the help embed (`core.js handleHelpCommand`) documents the `/radio` subcommands. Radio is independent of the cognition `/respond` path — it does not consume LLM tokens.

### Consequences

- Radio is a self-contained voice feature; failures are isolated from the character pipeline.
- The station catalog grows by editing `radioStations.js`; no protocol change.

---

## ADR-016: JS-side SQLite State Store

**Status:** Accepted  
**Date:** 2026-07-22

### Context

Guild config, user state, and chaos state were persisted as JSON files (`guildConfig.js`, `userState.js`, `chaosStatePersist.js`) with atomic-write `.tmp` rename. The Python side already uses SQLite (`packy_memory.py`). The JS hot path hits `getGuildConfig()` on every message with synchronous semantics, but JSON file writes race on concurrent mutations and load the entire config into memory at boot.

### Decision

Replace JSON-file persistence with SQLite via `node:sqlite` (Node 22+ built-in `DatabaseSync`) with `better-sqlite3` fallback. Three tables (`guild_config`, `user_state`, `chaos_state`) store JSON blobs per row, matching the Python schema pattern. One-shot JSON-to-SQLite migration on first boot, with `.migrated_sqlite` marker to prevent re-migration. Original JSON files are preserved (never deleted).

### Consequences

- Per-message config reads are single `SELECT` queries, not file reads.
- `setGuildConfig()` commits immediately via `UPSERT` — no race window.
- `saveGuildConfigs()` becomes a no-op (each write is already committed).
- `node:sqlite` is experimental in Node 22 but works without flags; `better-sqlite3` is the fallback.
- WAL mode ensures read concurrency for the bot's per-message hot path.

---

## ADR-017: Metrics + Sentry Observability

**Status:** Accepted  
**Date:** 2026-07-22

### Context

`logger.js` was a pure stdout `EventEmitter` — no counters, no gauges, no alerting. Nine `logger.error` sites in `index.js` vanished into stderr. A commercial bot needs observability before it can charge money (ADR-011/012).

### Decision

Add `src/bot/metrics.js` with a minimal interface: `counter(name, labels)`, `gauge(name, value, labels)`, `timing(name, ms, labels)`, `error(err, context)`. Default transport: in-memory ring buffer (100-error cap) flushed to `data/metrics.json` every 60s. Sentry lazy-inits from `SENTRY_DSN` if set; clean-clone safe without it. Per-command counters added to `core.js` and `system.js`. `/respond` latency timing added to `index.js`.

### Consequences

- A dev clone with no `SENTRY_DSN` still gets observability via `data/metrics.json`.
- Ring buffer caps errors at 100 to bound memory.
- `@sentry/node` is optional; only loaded when `SENTRY_DSN` is set.
- Metrics calls are layered alongside `logger.error` — no logging is removed.

---

## ADR-018: Composer Emergency Fallback (Cheap-LLM Fallback + Template Last-Resort)

**Status:** Accepted  
**Date:** 2026-07-23

### Context

`packy_cog_engine.py` is a `random.choice` template composer. Prior to this ADR, its output was prepended to the LLM system prompt in `/respond` (`packy_endpoint.py:617`), polluting the prompt with mad-libs. The workorder considered making the composer LLM-backed, but the actual call graph shows the composer feeds the LLM prompt, not a post-failure fallback. Making it LLM-backed would double per-request cost and latency.

### Decision

Remove the composer from the LLM prompt path entirely. The composer is now an **emergency fallback** that first attempts a cheap-LLM call (`PACKY_COMPOSE_MODEL`, default `claude-haiku-4-5-20251001`), then falls back to `random.choice` template filling if the cheap LLM also fails. The chain is: LLM primary → cheap-LLM fallback → template last-resort → "circuits fried" error string. The `llm_fn` is constructor-injected from `packy_endpoint.py` so the composer can call the cheap model without importing API client code.

### Consequences

- LLM prompt is no longer polluted with stochastic template output.
- On LLM failure, users get a cheap-LLM response first, then template fallback.
- `cognition_text` in `RespondResponse` indicates which fallback fired.
- `PACKY_COMPOSE_MODEL` env var selects the cheap model (default: claude-haiku-4-5-20251001).
- `PackyCogEngine.think()` is now async (awaited in `packy_endpoint.py`).

---

## ADR-019: Auth Required at Startup

**Status:** Accepted
**Date:** 2026-07-23

### Context

`PACKY_API_SECRET` defaulted to an empty string, which set `_bypass_auth = True`, meaning anyone reaching port 8765 had full access to the `/respond` endpoint. This normalized running without authentication.

### Decision

Require `PACKY_API_SECRET` at startup. If the env var is empty or not set and `PACKY_DEV_LICENSE != 1`, the server refuses to start (`SystemExit(1)`). With `PACKY_DEV_LICENSE=1`, the server boots with auth disabled (dev mode).

### Consequences

- Production deployments always have auth enabled.
- Dev mode requires explicit opt-in via `PACKY_DEV_LICENSE=1`.
- `.env.example` updated with descriptive placeholder for `PACKY_API_SECRET`.

---

## ADR-020: Vitest Migration

**Status:** Accepted
**Date:** 2026-07-23

### Context

5 JS test files used `console.log` + manual pass/fail counters with no assertion library, no mocking, no coverage. There was no way to run structured assertions or measure test coverage.

### Decision

Migrate all Node tests to Vitest with `describe/it/expect` blocks. Added `vitest.config.ts` with `singleFork: true` for SQLite test isolation. Added `test`, `test:ci`, `typecheck`, `fmt`, and `fmt:check` npm scripts.

### Consequences

- All 77 Node assertions now use Vitest's `expect()` API.
- Coverage report available via `npm run test:ci`.
- New assertions added for rate limiter status tracking, chaos score bounds, concurrent DB writes, and metric aggregation.
- CI smoke job updated to use `npm run test:ci`.

---

## ADR-021: Unified Python Dependencies

**Status:** Accepted
**Date:** 2026-07-23

### Context

Three dependency manifests existed: `requirements.txt`, `pyproject.toml`, and `uv.lock`. CI used `pip install -r requirements.txt` but modern Python uses `pyproject.toml`. Dependencies could drift between manifests.

### Decision

`pyproject.toml` is the single source of truth for Python dependencies. `requirements.txt` removed. CI and `Dockerfile.cognition` use `pip install -e ".[dev]"`. `uv.lock` tracked in git.

### Consequences

- No drift between dependency manifests.
- Deterministic builds via `uv.lock`.
- `stripe>=10.0` added to `pyproject.toml` (was imported but unlisted).
- `Dockerfile.cognition` updated to use `pip install -e .`.
