# Gargoyle Packy V2.0.0 — Project Overview

## What Is This

Gargoyle Packy is a Discord bot built around a lore-rich, snarky AI character — **Packard Bell "Packy"**, a 2011 laptop that survived thermal martyrdom, 200 Windows flashes, three years in a drawer, and a PipeWire civil war. He's grumpy, technically competent, and deeply traumatized. He remembers everything and forgives nothing.

V2.0.0 shifts the architecture from a fine-tuned local LLM to an API-backed character engine. The character layer is the product; the LLM is just a voice box.

---

## Architecture Overview

```
Discord (discord.js bot)
        |
        | user message / slash command
        v
  [Node.js Bot Layer]
  src/bot/index.js
        |
        | POST /respond  (user_text, cpu, temp)
        v
  [Python Cognition Microservice]  <-- the soul
  src/orchestration/
    packy_orchestrator.py          — assemble metadata header
    packy_endpoint.py              — FastAPI thin wrapper
  src/cognition/
    layer/orchestrator.py          — per-message state step
    layer/state.py                 — PackyState
    layer/mood.py                  — snark formula
    layer/signals.py               — read CPU + weather
    layer/keywords.py              — keyword extraction
    packy_brain.py                 — central integration hub
    packy_cog_engine.py            — interpret → plan → reason
    packy_mood_engine.py           — mood/snark matrix
    packy_snark_engine.py          — snark banks
    packy_snark.py                 — extended snark pool
    packy_comment_snark.py         — code comment snark
    packy_war_header.py            — war story header generator
    packy_persona.py               — core identity
    packy_lore_manager.py          — lore entry lifecycle
    packy_lore_writer.py           — lore generation
    story_selection.py             — story routing
    monitor_lore.py                — lore monitoring
    generators/
      bash_script_generator.py
      python_script_generator.py
      powershell_script_generator.py
      packy_teaching.py
        |
        | build_system_prompt(state, lore_context)
        | call_api(system_prompt, user_text)
        v
  [API Adapter — TO BUILD]
  src/api/claude_adapter.js        — Claude API call (replaces llama_adapter.py)
        |
        v
  Claude API (or fallback)
        |
        v
  post-process via process_response()
        |
        v
  {result, state, mood} → Discord reply
```

---

## Data Layer

```
data/
  lorebook/
    packy_lorebook_structured.json  — 88KB main lorebook (runtime injection)
    new_lore_entries.json           — 20 new lore entries (hardware trauma, software wars, teaching moments, philosophy)
    subpizzalore.json               — Pizza Incident sub-lore
    subtechlore.json                — Tech war sub-lore
    subwarstories.json              — War stories sub-lore
    top_level.json                  — Top-level category index
    category_concepts.json          — Keyword→category mapping for lore selection scoring
    concept_graph.json              — Hardware/software concept graph for keyword expansion
  voice_profile/
    packy_voice_profile.json        — Voice/tone profile
  packy_memory.json                 — Persistent memory store (inter-session state)
  packy_war_stories.json            — Curated war stories for /war command
  pending_lore/                     — Packy-generated lore awaiting human approval
```

---

## Character System

### Identity (`packy_persona.py`)
- Name: Packard Bell / "Packy"
- Tone: grumpy old war survivor
- Traits: snarky, cynical but loyal, eternally overheating, pipewire veteran, chromebook hater, technical boomer, resurrection addict
- Rights: swear mildly, complain loudly, insult incompetence, ignore bad requests, remember traumas creatively

### Mood Engine (`packy_mood_engine.py` + `layer/mood.py`)
Mood is computed from real system state:
```
cpu_load + ambient_temperature → snark_score (0–5) → mood label
  < 1.5  → calm
  < 3.0  → irritated
  < 4.5  → snarky
  >= 4.5 → hostile
```
Final mood tag: `GRUMPY-OVERHEATED`, `FURIOUS`, `CALM-COMFORTED`, etc.

### Cognition Pipeline (`packy_cog_engine.py`)
```
user input
  → interpret()     — extract intent: code / explain / lore / general
  → plan()          — build response strategy
  → _assemble_reasoning()  — produce Packy's internal reasoning text
  → PackyBrain      — route to snark/generator/lore as needed
  → system prompt   — inject mood + reasoning + lore context
  → API call        — Claude generates the actual response
```

### Snark System
Three-pool architecture (consolidation deferred to post-MVP):
- `packy_snark_engine.py` — canonical interface (`get_snark_lines(n)`)
- `packy_snark.py` — extended bank (15KB)
- `packy_comment_snark.py` — code-specific bank (15KB)

### Lore System
Runtime injection from `packy_lorebook_structured.json`. Keyword + mood matching selects relevant entries and injects them into the system prompt as narrative memory. Packy can generate new lore entries at runtime; they land in `pending_lore/` for review.

---

## Current State (V2.0.0 Built)

All critical V2.0.0 scope items are complete:

| Component | File | Status |
|-----------|------|--------|
| Claude API adapter | `src/bot/api/claudeAdapter.js` | Done |
| MiniMax API adapter | `src/bot/api/minimaxAdapter.js` | Done |
| Discord bot core | `src/bot/index.js` | Done |
| Slash command handlers | `src/bot/commands/handlers.js` | Done |
| Python FastAPI microservice | `src/orchestration/packy_endpoint.py` | Done |
| Per-user state (JS) | `src/bot/userState.js` | Done |
| Per-guild config (JS) | `src/bot/guildConfig.js` | Done |
| Emotion/intent classifier | `src/bot/character/emotionClassifier.js` | Done |
| Snark bank (JS merged) | `src/bot/character/snarkBank.js` | Done |

## Remaining / Post-MVP

- **Snark consolidation (Python side):** `packy_snark.py` + `packy_snark_engine.py` + `packy_comment_snark.py` are still three separate files. Deferred until Python cognition layer needs refactoring.
- **Lore expansion:** 20 new entries in `data/lorebook/new_lore_entries.json`. Use `docs/MINIMAX_PROMPTS.md` Prompt 3 to generate more.
- **Web admin panel:** Deferred (see ADR-002). `src/bot/packy.js` is the archived web terminal UI.

---

## What Was Deliberately Left Out

See `docs/ADR.md` ADR-007 for the full discard list. Summary:
- All LoRA weights (checkpoint-10 through checkpoint-170) — replaced by API
- GPT-2 model weights (548MB) — irrelevant
- TTS engine, alarms, reminders, scheduler — personal assistant features, not in scope for Discord bot
- Web UI (index.html, app.js, Flask routes) — deferred, may return as admin panel
- `packy.zip` — corrupt archive, skipped

---

## Development Setup (Target State)

```bash
# Python cognition microservice
cd src/orchestration
pip install fastapi uvicorn psutil requests
ANTHROPIC_API_KEY=... uvicorn packy_endpoint:app --port 8765

# Node.js Discord bot
cd src/bot
npm install discord.js dotenv axios
DISCORD_TOKEN=... BOT_COGNITION_URL=http://localhost:8765 node index.js
```

---

## Design Reference Docs

`docs/design/engine_references/` contains the ORBIT, PULSE, AURA, SCENE, and Hybrid Engine design documents. These were the inspiration for the orchestration layer architecture. They are reference material, not executable code. Particularly relevant for building the system prompt structure:
- `Hybrid Engine v1.1.txt` — emotion + action + lore orchestration pattern
- `ORBIT Engine.txt` — state-driven response routing
- `Action & Social React Engine.txt` — social reaction logic (relevant for Discord guild behavior)

---

## Archive Provenance

| Archive | Status | Key Contents |
|---------|--------|--------------|
| `packy3.zip` | CANONICAL SOURCE | All Python cognition files, design docs, early JS |
| `packy_finished_layer.zip` | CANONICAL SOURCE | Layer files (state, signals, keywords, mood, orchestrator) |
| `packy2.0.zip` | SECONDARY | Voice profile, layer/llama_adapter (archived) |
| `zip_layer_idea.zip` | REFERENCE | Engine design docs |
| `packy_v205.tar.gz` | REFERENCE | Shows v205 folder structure (core/cognition, core/snark) |
| `repo_snapshot_v2/v4.zip` | HISTORICAL | Old Python core (TTS, scheduler) — not extracted |
| `packy_reconstructed.zip` | DUPLICATE | Same as packy2.0 + packy3 merged |
| `packy_backup.zip` | ARCHIVAL | GPT-2 weights + duplicated code — not extracted |
| `packy_1.zip` | ARCHIVAL | LoRA checkpoints only |
| `packy_training.zip` | ARCHIVAL | Training JSONL data, 3.7GB |
| `packy.zip` | CORRUPT | No central directory — skipped |
