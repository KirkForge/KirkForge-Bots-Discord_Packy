# AGENTS.md — Worker Contract for KirkForge-Bots-Discord_Packy (Gargoyle Packy V2)

*This file is the verifier contract for any AI agent working in this repo. Read it before starting. Follow it always. Violations are regressions.*

*Repo facts: Discord bot with a grumpy AI character "Packy" (2011 Packard Bell laptop). Dual stack: Node.js/discord.js bot (`src/bot/`) + Python FastAPI cognition microservice (`src/cognition/`, `src/orchestration/`). The Python `/respond` endpoint is the single LLM call path (ADR-010). Default branch: `dev`.*

---

## Repo-specific guidance (preserved from prior AGENTS.md)

### Project Overview

Discord bot with a grumpy AI character named "Packy" (2011 Packard Bell laptop). Two execution modes:

- **`direct`** (default): Node.js builds system prompt + calls API adapter directly *(legacy/removed per ADR-010)*
- **`microservice`**: Routes through Python FastAPI cognition service on port 8765 *(the live path)*

Primary entry point: `src/bot/index.js`

### Commands

```bash
# Run bot (uses BOT_MODE from env, default direct)
npm start

# Dev with auto-restart
npm run dev

# Register slash commands
node src/bot/commands/register.js

# Python cognition microservice (for microservice mode)
cd /path/to/GargoylePackyV2
uvicorn src.orchestration.packy_endpoint:app --port 8765
```

### Key Architecture

```
Discord → src/bot/index.js (discord.js)
           ├─ commands/    (register.js, handlers.js — slash commands with Discord embeds, rate limiting)
           ├─ character/   (state.js, mood.js, snarkBank.js, loreSelector.js, chaosState.js, systemPrompt.js, emotionClassifier.js)
           ├─ api/         (claudeAdapter.js, minimaxAdapter.js)
           └─ signals.js   (CPU load, weather via OpenWeatherMap)

src/cognition/   — Python: packy_brain.py, packy_cog_engine.py, mood/snark/lore engines,
                   packy_war_stories.py, packy_memory_tools.py, packy_persona_tools.py, packy_behavior_profiles.py
src/orchestration/ — Python: packy_endpoint.py (FastAPI), packy_orchestrator.py
```

### Character System (JS side)

- `state.js`: `PackyState` class with `{turn, snark, mood, cpu, temp, weather, keywords}`
- `mood.js`: `computeSnark(cpu, temp)` → 0–5, `computeMood(snark)` → FURIOUS/GRUMPY/IRRITATED/CALM
- `chaosState.js`: unprovoked commentary, mood swings, target lock, sabotage
- `snarkBank.js`: merged from three Python snark files (`snarkBank = {base, lore, chromebook, tech_humor, code_comments}`)
- `loreSelector.js`: keyword + mood matching against `data/lorebook/packy_lorebook_structured.json`
- `systemPrompt.js`: `buildSystemPrompt(state, loreEntries, snarkLines)` → token-budgeted prompt

### Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DISCORD_TOKEN` | Yes | — | Bot token |
| `BOT_MODE` | No | `direct` | `direct` or `microservice` |
| `PRIMARY_ADAPTER` | No | `claude` | `claude` or `minimax` |
| `ANTHROPIC_API_KEY` | If adapter=claude | — | |
| `MINIMAX_API_KEY` | If adapter=minimax | — | |
| `MINIMAX_GROUP_ID` | If adapter=minimax | — | |
| `OPENWEATHER_API_KEY` | No | — | Enables weather-based mood |
| `PACKY_LOCATION` | No | `London` | |
| `COGNITION_PORT` | No | `8765` | Microservice port |

### Docker

```bash
docker-compose up
```
Starts both `cognition` (Python FastAPI on 8765) and `bot` containers. Bot depends on cognition being healthy.

### Data

- `data/lorebook/packy_lorebook_structured.json` — main lorebook (88KB)
- `data/lorebook/subpizzalore.json`, `subtechlore.json`, `subwarstories.json` — category sub-lore
- `data/lorebook/category_concepts.json` — keyword→category concept map for lore scoring
- `data/lorebook/concept_graph.json` — hardware/software concept expansion graph
- `data/lorebook/new_lore_entries.json` — 20 new lore entries
- `data/packy_memory.json` — persistent inter-session memory store
- `data/packy_war_stories.json` — curated war stories for /war command
- `data/pending_lore/` — Packy-generated lore awaiting human review

### Backup

The `data/` directory contains all persistent state: guild configs, user stats, chaos state, lorebooks, and the audit log. Run this cron to back it up daily:

```cron
0 4 * * * cp -r /path/to/GargoylePackyV2/data /path/to/backups/data.$(date +\%Y\%m\%d)
```

Keep at least 30 days of backups. For git-based config tracking:

```bash
cd /path/to/GargoylePackyV2 && git add data/guild_config.json data/chaos_state.json data/user_state.json && git commit -m "chore(data): snapshot config state"
```

### Important Quirks

- **Lorebook loading**: done on `client.ready` event in `src/bot/index.js:413`; path resolved relative to `src/bot/`
- **Emotion classifier**: `emotionClassifier.js` injects synthetic tokens (e.g. `emo_frustrated`, `intent_rant`, `topic_hardware`) into the lore selection scoring haystack — this is how user intent shapes lore recall
- **Command handlers**: `commands/handlers.js` is the implementation for slash commands (embeds, rate limiting, mood-colored UI); `commands/register.js` only handles API registration
- **Unprovoked commentary**: chaos layer fires on ALL messages in a channel (not just mentions), rate-limited per channel
- **Rate limiting**: 3 requests per 10 seconds per user (in-memory Map, not persisted)
- **Python path hack**: `packy_endpoint.py:21` adds `project_root` to `sys.path` so imports like `from src.cognition...` work
- **Snark consolidation**: Three Python snark files merged into single `snarkBank.js`; the original Python files (`packy_snark_engine.py`, `packy_snark.py`, `packy_comment_snark.py`) are still present and used by the Python cognition layer
- **`src/orchestration/packy_entry_ref.py`**: archived reference entry point (CLI loop using old llama_adapter) — not active
- **`src/orchestration/small orchistrator.py`**: draft/scratch file with space in name — reference only, not imported
- **`src/bot/packy.js`**: web terminal UI (not Discord) — not the active entrypoint

---

## 1. Plan mode default
- Before writing any code, write a plan to `workplan.md` (gitignored). The plan must list the files you will touch (full paths), state the root cause you're fixing (not the symptom), and state the gate you'll run to verify.
- Check `workplan.md` before implementation. Check `lessons.md` for lessons from prior sessions. Check `state.md` for current repo state.
- If the task is unclear, say so in `workplan.md` and escalate — do not guess.

## 2. Subagent strategy
- For complex multi-step tasks, break them into subtasks and dispatch subagents.
- Each subtask must have a clear scope (files to touch), a gate (command to run), and a done-condition.
- Do not dispatch a subagent for a task you can do in <5 minutes yourself.

## 3. Self-improving loop
- At session end, write `lessons.md` (gitignored) with: what you learned about this codebase (conventions, gotchas, patterns), what you tried that didn't work and why, what you'd do differently next time.
- Update `state.md` (tracked) with: what changed this session, what's pending, what's blocked.
- Lessons from `lessons.md` that are permanent conventions get folded into this `AGENTS.md` file — so the next worker reads them automatically.

## 4. Verification
- Run the gates before every commit. Paste the actual output (not paraphrased). A green claim requires the pasted output + the head SHA. "It passed" is not evidence.
- Gates for this repo (DUAL stack — run both):
  - Test (Python): `pytest` (`testpaths = ["test", "tests"]`)
  - Test (Node): `npm test` (smoke); `npm run test:all` (smoke + integration: `test:integration/rateLimiter.test.js` + `test:integration/guildConfig.test.js`)
  - Lint (Node): `npm run lint` (`eslint src/`)
  - Lint (Python): `uv run ruff check` (`target-version py311`, `line-length 100`, `E402` ignored for sys.path pattern)
  - Fmt (Python): `uv run ruff format --check` (`uv run ruff format` to write)
  - Fmt (Node): n/a (no prettier configured in this repo)
  - Typecheck: n/a (no `tsc`/`mypy` configured in this repo — `tsconfig.json` is gitignored/empty placeholder)
- Do not rewrite tests to make them pass. Fix the root cause.
- Do not add `|| true`, `|| echo "non-fatal"`, `#[ignore]` to make red go green.

## 5. Demand elegance
- Small, pure, well-named functions. No dead code. No debug spam (`console.log`, `print(`) in committed code.
- Match the existing style. Node side: ESM (`"type": "module"`), discord.js conventions, `src/bot/character/` module layout. Python side: `ruff` with `line-length 100`, `E402` ignored for the `sys.path` hack pattern.
- Preserve honest-doc annotations (`ponytail:`, `ceiling:`, `upgrade path:`) — they document known limitations. Removing them is a regression.
- Dead code noted in `state.md`: `small_orchestrator.py`, `packy_entry_ref.py`, `src/bot/packy.js`, three separate Python snark files (ADR-006 deferred). Don't add more; consider removing when in scope.
- A change that adds 100 lines to fix a 3-line bug is probably wrong. Find the smaller change.

## 6. Autonomous bug fixing
- If a test fails, read the error. Find the root cause. Fix it.
- Do NOT: rewrite the test to pass, add `|| true`, lower a threshold, delete the assertion, add `#[ignore]` to make red go green.
- Do NOT: add debug logging to committed code. Use `workplan.md` for scratch notes.
- If you've attempted the same fix 3 times and it's still red, STOP. Write "ESCALATE: <root cause unknown>" in `lessons.md` and return. The brain takes over when the brawn is stuck.

## Task management
1. **Plan**: write `workplan.md` (gitignored) with files to touch + root cause + gate.
2. **Check before implementation**: read `workplan.md`, `lessons.md`, `state.md`, and this `AGENTS.md`.
3. **Check progression**: after each file edit, verify it compiles/lints. Don't batch 10 changes then discover the 3rd was wrong.
4. **Explain changes**: post a summary in `workplan.md` (what changed, why) and a one-liner in `CHANGELOG.md` (it exists).
5. **Session close**: commit → write `lessons.md` (what I learned) → update `state.md` (what changed, what's pending) → `CHANGELOG.md` one-liner → verify clean tree → verify gates green → paste final gate output. Session is NOT done until all 6 are done.
6. **Worktree discipline**: work in an isolated worktree off `origin/dev` (this repo's default branch is `dev`). `git fetch && git reset --hard origin/dev` before starting. Never touch `dev`/`main` directly. Never force-push. Fix forward.
7. **Scope discipline**: touch only the files the task names. If you need to edit outside scope, note it in `lessons.md` as "scope creep: <file> because <reason>".
8. **Honesty over claim**: paste gate output, never say "green" without the run ID + head SHA. An ADR that overclaims is a regression. A "CI green" citation for the wrong run ID is a regression.

## Escalation
If you are stuck after 3 attempts, say so. Write "ESCALATE: <root cause unknown>" in `lessons.md`. The brain (frontier model) takes over. This is not a failure — it's the design: the Fiat knows when to call the tow truck.