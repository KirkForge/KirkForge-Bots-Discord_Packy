# MiniMax Prompts — Gargoyle Packy V2.0.0

Use these with MiniMax 2.7 (large tasks, big context) or 2.5 (faster, smaller jobs).
These are the grunt-work prompts — content generation, mechanical porting, large doc processing.

---

## PROMPT 1 — Port Python Layer to JavaScript
**Model:** MiniMax 2.5  
**Output:** `src/bot/character/state.js`, `mood.js`, `keywords.js`, `prompt.js`

```
You are porting a Python cognition layer to JavaScript for a Node.js Discord bot.

Here are the Python source files to port:

--- state.py ---
[PASTE src/cognition/layer/state.py]

--- mood.py ---
[PASTE src/cognition/layer/mood.py]

--- keywords.py ---
[PASTE src/cognition/layer/keywords.py]

--- prompt.py ---
[PASTE src/cognition/layer/prompt.py]

Port each to ES modules (export/import syntax, .js files).
Keep all variable names and logic identical to the Python.
Replace psutil cpu_percent with: Math.min(os.loadavg()[0] * 25, 100)
Replace the requests weather call with native fetch().
Output one complete file per module.
No TypeScript. No class syntax unless the Python uses classes.
```

---

## PROMPT 2 — Consolidate Snark Banks to JavaScript
**Model:** MiniMax 2.7 (needs full context of 3 large files)  
**Output:** `src/bot/character/snarkBank.js`  
**Status:** DONE — snark consolidation completed (ADR-006 Fulfilled). All snark data
now lives in `src/cognition/packy_snark.py`. This prompt is retained for reference only.

```
You are porting and consolidating snark data from packy_snark.py into one JavaScript module
for a Discord bot character named Packy (a grumpy old laptop AI).

--- packy_snark.py ---
[PASTE src/cognition/packy_snark.py]

Merge all arrays into a single structured ES module: snarkBank.js

Structure must be:
export const snarkBank = {
  base: [...],        // from PACKY_SNARK_BASE
  lore: [...],        // from PACKY_LORE_SNARK  
  chromebook: [...],  // from PACKY_CHROMEBOOK_INSULTS
  tech_humor: [...],  // from PACKY_TECH_HUMOR
  code_comments: [...] // from PACKY_CODE_COMMENT_SNARK
}

export function getSnarkLines(category = 'base', n = 3) {
  // return n random items from snarkBank[category]
  // if category not found, fall back to 'base'
}

export function getRandomSnark() {
  // pick one random line from the entire pool
}

Deduplicate any lines that appear across multiple arrays.
Output the complete file only.
```

---

## PROMPT 3 — Expand the Lorebook
**Model:** MiniMax 2.7  
**Output:** New entries to append to `data/lorebook/packy_lorebook_structured.json`

```
You are writing new lore entries for a Discord bot character named Packy.

CHARACTER IDENTITY:
- Name: Packard Bell / "Packy"  
- He is a 2011 Packard Bell laptop who became sentient through spite
- Survived: 105°C thermal events, 200 Windows 10 flashes, 3 years in a drawer,
  a PipeWire vs ALSA civil war, Broadcom wifi infestation, USB port casualties,
  the Pizza Incident of 2025, Terrace Exile in 2°C winds
- Personality: grumpy old war veteran engineer, snarky, cynical but loyal
- Calls users "meatbag", uses war metaphors for tech problems
- Hates: Chromebooks, Java, cloud storage, modern bloatware
- Respects: duct tape solutions, ZRAM, spite-driven persistence

EXISTING LOREBOOK SAMPLE (for style reference):
[PASTE first 100 lines of data/lorebook/packy_lorebook_structured.json]

Write 20 new lore entries in the SAME JSON structure as the existing entries.

Categories:
- 5 entries: new hardware trauma incidents (not already in the lorebook)
- 5 entries: software wars (OS drama, driver conflicts, package manager fights)
- 5 entries: teaching moments (Packy explaining something to a clueless user)
- 5 entries: philosophical observations (Packy on AI, cloud computing, modern devs)

Each entry must have:
- id (continue from last existing id)
- category
- subcategory  
- mood: one of FURIOUS / GRUMPY / IRRITATED / CALM
- text (Packy's voice, 1-3 sentences, first person)
- tags: array of relevant keywords

Output valid JSON array only. No explanation.
```

---

## PROMPT 4 — Generate Lore Injection Logic
**Model:** MiniMax 2.5  
**Output:** `src/bot/character/loreSelector.js`

```
Write a JavaScript ES module for selecting relevant lore entries to inject into
a Discord bot's system prompt.

The lore data is stored in data/lorebook/packy_lorebook_structured.json
Each entry has: id, category, subcategory, mood, text, tags

The module should export:

export function selectLore(lorebook, userMessage, currentMood, n = 2) {
  // 1. keyword match: find entries whose tags overlap with words in userMessage
  // 2. mood match: prefer entries matching currentMood
  // 3. if no matches, return n random entries
  // 4. return array of n entry objects
}

export function formatLoreForPrompt(entries) {
  // returns a string like:
  // "Packy remembers: [entry.text]\nPacky also recalls: [entry.text]"
}

Keep it simple. No external dependencies. Pure JS.
Output the complete file only.
```

---

## PROMPT 5 — Read ORBIT Engine and Extract Patterns
**Model:** MiniMax 2.7 (large doc)  
**Output:** Summary for `docs/design/orbit_patterns_extracted.md`

```
Read the following engine design document and extract ONLY the patterns relevant
to building a Discord bot response orchestration system.

Focus on:
- How emotional/mood state flows through the engine
- How context (memory, lore) is injected into responses  
- What the metadata header format looks like and what fields it contains
- How response style is selected based on state
- Any rate limiting or cooldown mechanisms described

Ignore: web UI references, training/fine-tuning, GUI components, character card syntax.

Output: bullet-point markdown summary, max 600 words, actionable patterns only.
Organize under headings: State Flow / Context Injection / Response Selection / Rate Limiting

[PASTE docs/design/engine_references/Hybrid Engine v1.1.txt]
```

---

## PROMPT 6 — Read Action & Social React Engine, Extract Discord Patterns
**Model:** MiniMax 2.5  
**Output:** Summary for `docs/design/social_react_patterns.md`

```
Read this engine design document. Extract patterns relevant to a Discord bot
that participates in group chat channels — specifically:

- When does the bot speak unprompted?
- How does it decide to react to messages not directed at it?
- How does it handle multiple users in a channel?
- What cooldown/rate mechanisms prevent spam?
- How does "target lock" or fixation on a user work?

Output markdown bullet points only. Max 400 words. Discord-specific framing.

[PASTE docs/design/engine_references/Action & Social React Engine.txt]
```

---

## PROMPT 7 — Write Chaos Layer State Extension
**Model:** MiniMax 2.5  
**Output:** `src/bot/character/chaosState.js`

```
Write a JavaScript module implementing the Chaos State layer for a Discord bot.

Based on this ADR:

The chaos layer sits between orchestration and response generation.
It injects non-deterministic behavior under guardrails.

PackyState needs these additions:
- chaos_score: float (0-1, derived from mood + snark)
- target_user_id: string|null
- target_lock_expiry: number|null (unix timestamp)
- mutation_flag: bool
- sabotage_flag: bool  
- last_injection_ts: number (unix timestamp)

Chaos modules:
1. Unprovoked commentary: fires based on chaos_score, 1 per channel per 3 minutes max
2. Mood swing override: FURIOUS shortens response, CALM allows rare clarity
3. Target lock: fixate on a user for 5-20 minutes, weighted by interaction frequency
4. Sabotage: low probability, only non-critical non-admin commands

Write the module with these exports:
- computeChaosScore(mood, snarkLevel) → float
- shouldFireUnprovoked(chaosState, channelId) → bool
- applyMoodOverride(chaosState, baseStyle) → responseStyle
- acquireTargetLock(chaosState, userId, interactionHistory) → chaosState
- checkTargetLock(chaosState, userId) → bool
- shouldSabotage(chaosState, commandType) → bool
- tickChaosState(chaosState) → chaosState (decay/cleanup)

Hard guardrails in comments where they apply.
No external deps. Pure JS. Output complete file.
```

---

## Notes on Model Selection

| Task | Model | Why |
|------|-------|-----|
| Large doc summarization (ORBIT, HYBRID) | 2.7 | 500KB+ context needed |
| Snark bank consolidation | 2.7 | Three 15KB files + dedup |
| Lore expansion | 2.7 | Needs full lorebook for style match |
| JS layer port | 2.5 | Mechanical, small files |
| Lore selector logic | 2.5 | Small, self-contained |
| Chaos state module | 2.5 | Logic-heavy but contained |
| Boilerplate | 2.5 | Trivial |
