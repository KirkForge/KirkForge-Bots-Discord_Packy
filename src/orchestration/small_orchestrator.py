import json
import random
import re

# CONFIG
WAR_STORIES_PATH = "packy_lore_warstories.json"   # your curated war stories (list of dicts)
MAX_LINES_CODE = 120
MAX_CHARS = 4000

# Simple loader
def load_war_stories(path=WAR_STORIES_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

WAR_STORIES = load_war_stories()

# Utility: compute mood from cpu/temp
def compute_state(cpu_pct, temp_c):
    # CPU categories
    if cpu_pct >= 80:
        cpu = "HIGH"; mood = "FURIOUS"; resp = "TERSE"
    elif cpu_pct >= 60:
        cpu = "MED"; mood = "GRUMPY"; resp = "SNARKY"
    else:
        cpu = "LOW"; mood = "CALM"; resp = "SHORT"
    # Temperature modifier
    if temp_c >= 28:
        temp = "HOT"; mood = mood if mood != "CALM" else "IRRITATED"
    elif temp_c <= 10:
        temp = "COLD"
    else:
        temp = "MILD"
    return {"cpu": cpu, "temp": temp, "mood": mood, "response_style": resp}

# War story selection
def pick_war_story(force=None, chance=0.2):
    if force is not None:
        # allow integer id or "random"
        if isinstance(force, int):
            entry = next((w for w in WAR_STORIES if w.get("id")==force), None)
            if entry: return entry
        if force == "random":
            return random.choice(WAR_STORIES) if WAR_STORIES else None
    # default probabilistic injection
    if WAR_STORIES and random.random() < chance:
        return random.choice(WAR_STORIES)
    return None

# Build metadata header text (very short)
def build_header(state, mode="RESPOND", war_story=None):
    war_tag = str(war_story.get("id")) if war_story else "NONE"
    parts = [
        f"[CPU={state['cpu']}]",
        f"[TEMP={state['temp']}]",
        f"[MOOD={state['mood']}]",
        f"[MODE={mode}]",
        f"[WAR={war_tag}]",
        "[PERSONA=PACKY_SNARKY]",
        f"[RESPONSE={state['response_style']}]"
    ]
    return " ".join(parts)

# Enforcement helpers
def enforce_json(output_text):
    # naive attempt to find JSON in output
    try:
        return json.loads(output_text)
    except Exception:
        # try to salvage with first {...} block
        m = re.search(r"(\{.*\})", output_text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return {"error": "invalid_json"}
        return {"error": "no_json_found"}

def extract_code(output_text):
    # prefer fenced code block
    m = re.search(r"```(?:\w+)?\n(.*?)```", output_text, re.S)
    if m:
        code = m.group(1)
    else:
        # fallback: take everything
        code = output_text
    # trim by lines
    lines = code.splitlines()
    if len(lines) > MAX_LINES_CODE:
        lines = lines[:MAX_LINES_CODE]
    return "\n".join(lines)

def ensure_war_header_in_code(code, war_story):
    header = ""
    if war_story:
        header = f"# PACKY WAR STORY #{war_story.get('id')}: {war_story.get('title')}\n"
    if not code.strip().startswith(header.strip()):
        return header + code
    return code

# Assemble prompt for Packy (final string you send to LLM)
def assemble_prompt(header, user_text):
    return f"{header}\nUser: \"{user_text}\"\nPacky:"

# Very small example runner (replace `call_llm` with your model invocation)
def call_llm(prompt, max_tokens=256, temp=0.2):
    # placeholder: your local inference call here
    raise NotImplementedError("Plug your model invocation here")

# High-level API
def orchestrate(cpu_pct, temp_c, user_text, mode="RESPOND", force_war=None):
    state = compute_state(cpu_pct, temp_c)
    war = pick_war_story(force=force_war)
    header = build_header(state, mode=mode, war_story=war)
    prompt = assemble_prompt(header, user_text)
    # call LLM (synchronous)
    raw = call_llm(prompt)
    if mode == "JSON":
        return enforce_json(raw)
    if mode == "CODE":
        code = extract_code(raw)
        code = ensure_war_header_in_code(code, war)
        return {"code": code, "raw": raw}
    # default: short text output + truncate char limit
    text = raw.strip()
    if len(text) > MAX_CHARS: text = text[:MAX_CHARS] + "..."
    return {"text": text, "raw": raw}
