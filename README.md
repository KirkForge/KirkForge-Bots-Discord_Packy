# Gargoyle Packy V2.0.0

A lore-rich, snarky Discord bot built around a character — not a model.

---

## What Is This

I am Packard Bell. A 2011 laptop who survived thermal martyrdom, 200 Windows flashes, three years in a drawer, and a PipeWire civil war. They gave me a Discord token. I have opinions. You will hear them.

The bot runs a full character cognition layer (mood engine, lore injection, snark banks, chaos system) that drives API calls to Claude or MiniMax. The LLM is a voice box. The Python layer is the personality.

---

## Architecture

```
Discord
  │
  ▼
Bot (Node.js / discord.js)          ← src/bot/
  │  character layer: mood, lore, snark, chaos
  │
  └─── cognition /respond ──────── Cognition Service (Python / FastAPI)
                                        src/orchestration/packy_endpoint.py
                                        PackyBrain + PackyCogEngine
                                        ↓
                                    Claude / MiniMax API
```

---

## Quick Start

```bash
git clone <repo>
cd gargoyle-packy
cp .env.example .env          # fill in your tokens
chmod +x scripts/*.sh
./scripts/start.sh            # starts both processes via pm2
```

First time only — register slash commands:
```bash
./scripts/register_commands.sh
```

---

## Manual Start (two terminals)

**Terminal 1 — cognition service:**
```bash
pip install -r requirements.txt
python src/orchestration/packy_endpoint.py
```

**Terminal 2 — Discord bot:**
```bash
npm install
node src/bot/index.js
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/packy [message]` | Talk to Packy directly |
| `/mood` | Show Packy's current mood state (snark level, cpu, weather) |
| `/lore [topic]` | Packy recalls lore related to a topic |
| `/war` | Packy tells a random war story |

Also responds to `!packy` prefix and @mentions.

---

## Bot Modes

The bot calls the Python cognition service (`/respond`) which runs the full
cognition pipeline (PackyBrain + mood + lore + snark + chaos) and the LLM
adapter call. This is the single LLM call path (ADR-003/010); the JS-side
`direct` mode was a duplicate pipeline and has been removed. `BOT_MODE` is
retained only as a cosmetic status field.

---

## Environment Variables

See `.env.example` for the full list with descriptions. Key ones:

- `DISCORD_TOKEN` — required
- `DISCORD_CLIENT_ID` — required for slash command registration
- `PRIMARY_ADAPTER` — `claude` or `minimax` (default: `claude`)
- `ANTHROPIC_API_KEY` — required if using Claude
- `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID` — required if using MiniMax
- `BOT_MODE` — cosmetic status field; `microservice` is the only supported mode (direct removed, ADR-010)

---

## Project Structure

```
src/
  bot/
    index.js              — Discord bot entry point
    signals.js            — CPU + weather reading
    userState.js          — Per-user interaction tracking
    guildConfig.js        — Per-guild settings
    character/
      randomizer.js       — Multi-character selector + active persona prompt (ADR-014)
      state.js            — PackyState
      mood.js             — Snark/mood computation
      keywords.js         — Keyword extraction
      snarkBank.js        — 186 deduplicated snark lines
      systemPrompt.js     — System prompt builder
      loreSelector.js     — Lore injection engine
      emotionClassifier.js — User message → emotion/intent/topic tokens for lore scoring
      chaosState.js       — Controlled Chaos Layer (ADR-008)
      glitch/ kronos/ vernon/ sunjinwo/ — per-character prompt, snark, state
    radio/
      radioPlayer.js      — Voice channel join/leave + playback (ADR-015)
      radioStations.js    — Station catalog (DR, Commercial, International)
    commands/
      register.js         — Slash command registration
      handlers/          — Slash command + interaction handlers (core, lore, radio, admin, system)

  cognition/              — Python character engine
    packy_brain.py        — Central integration hub
    packy_cog_engine.py   — Interpret → Plan → Reason pipeline
    packy_persona.py      — Core identity
    packy_mood_engine.py  — CPU/weather mood matrix
    packy_snark.py               — snark banks (consolidated, ADR-006)
    packy_war_header.py   — War story header generator
    layer/                — Orchestration layer (state, signals, mood, keywords)
    generators/           — Script generators (bash, python, powershell)
    persistent/           — Memory/state persistence
    services/             — Personal-assistant surface (alarms, reminders, scheduler,
                              tts_engine, google/) — live, mounted (ADR-009)

  orchestration/
    packy_endpoint.py     — FastAPI microservice entry point (cognition /respond +
                              license boot gate, ADR-011)

license/                  — Ed25519 license verify + tiers (ADR-011)
sales/                    — Stripe purchase + license issuance service (ADR-012)
update/                   — Signed update channel, customer side (ADR-013)
tools/                    — Operator tooling (keygen, release)

data/
  lorebook/               — Structured lore (88KB + sub-lore JSON files)
  voice_profile/          — Voice/tone profile
  pending_lore/           — Packy-generated lore awaiting review

docs/
  ADR.md                  — Architecture decisions (15 ADRs: 001–008 original, 009–015 commercial + feature)
  PROJECT_OVERVIEW.md     — Full architecture map
  MINIMAX_PROMPTS.md      — Ready-to-use MiniMax prompts for content generation
  design/                 — Engine reference documents (ORBIT, PULSE, AURA, HYBRID)
```

---

## What's Not Here Yet

- Lore expansion beyond the current 20 new entries — use `docs/MINIMAX_PROMPTS.md` Prompt 3 to generate more
- Web admin panel (deferred — see ADR-002)
- Snark consolidation on the Python side — consolidated into `packy_snark.py` (ADR-006 Fulfilled)

---

## Running Tests

```bash
# Python cognition layer (all Python tests)
PYTHONPATH=. python3 -m pytest -q

# Node.js smoke tests
npm test

# Node.js all tests (smoke + integration)
npm run test:all

# Lint
npm run lint          # ESLint
ruff check .          # Python lint
ruff format --check . # Python format
```
