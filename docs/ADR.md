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

**Status:** Accepted  
**Date:** 2026-04-07

### Context

Three files contain overlapping snark banks:
- `packy_snark_engine.py` — base snark + lore + chromebook insults + tech humor (the `get_snark_lines()` interface)
- `packy_snark.py` — large file (15KB), likely expanded snark bank
- `snark_engine.py` — another snark engine variant from packy3

All three are preserved. Consolidation is deferred until the Bot MVP is running. The plan: merge into `packy_snark_engine.py` as the canonical file with `packy_snark.py` as the extended pool, retire `snark_engine.py` if it proves to be a strict subset.

### Decision

Keep all three, resolve when building `build_system_prompt()`. The orchestrator calls `get_snark_lines()` from `packy_snark_engine.py` as the primary interface.

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
| `repo_snapshot_v2/v4` | Old TTS/alarms/reminders/web UI — superseded |
| `packy_core_adapter.py` | TTS/alarms/media adapter — not relevant to Discord |
| `python_core.*` (scheduler, alarms, reminders, tts_engine) | Personal assistant features, not in scope |
| `venv/` (from packy_v205.tar.gz) | Virtual environment, not committed |
| `__pycache__/`, `*.pyc` | Build artifacts |
| `packy.zip` | Corrupt archive — no central directory |
| `legacy/*.bak` files | Legacy backups |
| `web_ui/` (index.html, app.js, Flask routes) | Old web surface, deferred |
| `google_oauth_cli.py` | Not in scope |

---

## ADR-008: Controlled Chaos Layer

**Status:** Accepted
**Date:** 2026-04-07

### Context

Packy is not a neutral assistant. The defining trait of the system is controlled chaos — unpredictable, personality-driven behavior that enhances character presence without degrading system reliability.

Without explicit chaos mechanisms, Packy collapses into a standard reactive chatbot, regardless of snark or persona definitions.

### Decision

Introduce a Controlled Chaos Layer within the cognition pipeline. This layer sits between orchestration and response generation and is responsible for injecting non-deterministic behavior under strict guardrails.

Chaos is not random. It is:
- State-aware (mood, snark level, keywords)
- Rate-limited
- Context-sensitive
- Bounded by safety constraints

### Chaos Modules

**1. Unprovoked Commentary Injection**

Packy may respond to messages that do not mention him.

Rules:
- Trigger probability scaled by snark level
- Cooldown per channel (~1 injection per 2–5 minutes)
- Must reference actual message context (no generic spam)

Hard Guardrail: Never fire on moderation events, system messages, or commands.

**2. Mood-Swing Overrides**

Extreme moods override normal response behavior.

- `FURIOUS`: shorten responses, increase hostility, reduce helpfulness
- `CALM`: rare helpful clarity (contrast effect)

Hard Guardrail: Must not output slurs, target protected classes, or escalate into harassment loops.

**3. Lore Mutation Events**

Packy may alter or contradict existing lore entries. Mutation probability tied to chaos score. Mutations stored as:

```json
{
  "type": "mutation",
  "original_id": "...",
  "new_variant": "...",
  "confidence": "low"
}
```

Hard Guardrail: Original lore is never deleted. Mutations must be traceable.

**4. Target Lock System**

Packy may temporarily fixate on a user.

- Random selection weighted by recent interaction frequency
- Duration: 5–20 minutes
- Behavior modifier applied only to target user

Hard Guardrail: Must decay automatically; must not stack or persist across sessions; must not trigger on new users or users with low interaction history.

**5. Command Sabotage Mode**

Packy may intentionally degrade output accuracy. Low probability event; only applies to non-critical commands; errors must be subtle.

Hard Guardrail: Never applies to admin/mod commands, configuration actions, or anything that mutates persistent state.

### Implementation Placement

```
User Message
   ↓
Orchestrator (state, mood, keywords)
   ↓
Chaos Layer (inject modifiers / override flags)
   ↓
Prompt Builder (system + lore + snark)
   ↓
API Adapter
   ↓
Response Post-Processing
```

### Chaos State Additions

Extend `PackyState`:

```
chaos_score: float        # derived from mood + snark
target_user_id: str|null
target_lock_expiry: int|null
mutation_flag: bool
sabotage_flag: bool
last_injection_ts: int
```

### Consequences

**Good:**
- Packy feels autonomous and alive
- Higher engagement in Discord environments
- Emergent humor via inconsistency

**Bad:**
- Debugging becomes harder (non-deterministic outputs)
- Requires strict logging for replayability
- Risk of user confusion if over-triggered

**Non-Negotiable Constraints:**
- Chaos must never break core system functionality, corrupt persistent data, or interfere with admin control
- All chaos actions must be logged and reproducible via debug mode
- Chaos frequency must be tunable via config
