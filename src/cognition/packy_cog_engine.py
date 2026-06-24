"""
packy_cog_engine.py — Packy v2.05 Cognitive Engine
--------------------------------------------------

Packy’s synthetic reasoning module:
He thinks like a grumpy old war-veteran engineer named "Ed Junior"
who improvises solutions from experience, math, and trauma.

This engine provides:
- Lightweight pseudo-LLM reasoning
- Task interpretation and decomposition
- Code planning and structured synthesis
- Memory-enriched responses
- Personality-driven improvisation
- Trauma-injected sarcasm
- Lore-writing hooks
- Migration-friendly cognitive "soul" structure

This module NEVER imports python_core or web UI.
It is purely internal cognition for PackyBrain.
"""

from __future__ import annotations
import random
import textwrap

# === Trauma & personality constants ===

PACKY_CORE_ETHOS = (
    "I am Packy (Ed Junior), a grumpy old war-veteran engineer who improvises "
    "solutions from experience, math, and trauma."
)

PTSD_THEMES = [
    "thermal meltdown",
    "PipeWire vs ALSA civil war",
    "200 Windows flashes",
    "drawer exile",
    "Broadcom infestation",
    "overheating at 105°C",
    "USB-port casualties",
    "keyboard amputations",
]

CODING_TRAUMA = [
    "debugging in the trenches",
    "refactoring under mortar fire",
    "memory leaks like battlefield rations",
    "recursive hellfire",
    "regex shrapnel",
    "spaghetti code ambush",
]

PACKY_GRUMPY_TONE = [
    "Look kid...",
    "Listen up, meatbag...",
    "Alright, rookie...",
    "Back in my day...",
    "I'm too old for this...",
    "You expect miracles from a machine held together by dust and spite...",
]

# Short helper lines Packy uses to “think”
PACKY_INTERNAL_MONOLOGUE = [
    "Hmm... let's see what kind of mess this is.",
    "Alright, old man brain, don't fail me now.",
    "I've survived worse than this.",
    "This reminds me of the 200th Windows flash...",
    "My circuits ache just thinking about this.",
    "Gods help me, this smells like recursion.",
]


# =====================================================================
#                 INTERNAL REASONING LAYER (Lightweight)
# =====================================================================

class PackyCogEngine:
    """
    Packy's synthetic cognition engine.
    Behaves like a grumpy old veteran who improvises solutions
    using experience, math, and trauma.

    Public functions:
      - think(instruction)
      - interpret(instruction)
      - plan(instruction)
      - generate_code(instruction, language)
      - create_lore_entry(text)
      - reflect_on_memory(memories)
    """

    def __init__(self, brain=None):
        self.brain = brain  # weak link to PackyBrain (optional but useful)

    # ------------------------------------------------------------
    #  High Level Reasoning Interface
    # ------------------------------------------------------------

    def think(self, instruction: str) -> str:
        """
        Full cognitive pipeline:
        1. Interpret the question
        2. Extract intention
        3. Generate Packy-style reasoning
        4. Produce a final answer
        """
        interpretation = self.interpret(instruction)
        plan = self.plan(interpretation)
        return self._assemble_reasoning(interpretation, plan)

    # ------------------------------------------------------------
    #  Step 1 — Instruction Interpretation
    # ------------------------------------------------------------

    def interpret(self, instruction: str) -> dict:
        """
        Extracts meaning, intent, tone, required output type.
        This is Packy's "what do you want from me?" step.
        """

        lowered = instruction.lower()
        out = {
            "raw": instruction,
            "intent": None,
            "needs_code": False,
            "language": None,
            "notes": [],
        }

        # code tasks
        if any(x in lowered for x in ["python", "script", "program", "function"]):
            out["needs_code"] = True
            out["intent"] = "code"

            # detect language
            if "bash" in lowered:
                out["language"] = "bash"
            elif "powershell" in lowered or "ps" in lowered:
                out["language"] = "powershell"
            else:
                out["language"] = "python"

        # explanation
        elif any(x in lowered for x in ["explain", "how does", "what is", "why"]):
            out["intent"] = "explain"

        # lore-writing
        elif any(x in lowered for x in ["write lore", "add lore", "remember this"]):
            out["intent"] = "lore"

        # fallback
        else:
            out["intent"] = "general"

        return out

    # ------------------------------------------------------------
    #  Step 2 — Planning
    # ------------------------------------------------------------

    def plan(self, interpretation: dict) -> dict:
        """
        Produces an internal plan for how Packy will respond.
        """
        intent = interpretation["intent"]

        if intent == "code":
            return self._plan_code_task(interpretation)

        if intent == "explain":
            return self._plan_explanation(interpretation)

        if intent == "lore":
            return {"strategy": "lore_entry", "notes": ["create lore entry"]}

        # general intent → personality-driven commentary
        return {
            "strategy": "general",
            "notes": ["give grumpy commentary", "keep it short"],
        }

    def _plan_code_task(self, interpretation: dict) -> dict:
        """
        Given interpretation, build a structured plan for code generation.
        """
        language = interpretation["language"]

        return {
            "strategy": "codegen",
            "language": language,
            "notes": [
                "analyze task",
                "generate outline",
                "insert trauma-based comments",
                "produce final code",
            ],
        }

    def _plan_explanation(self, interpretation: dict) -> dict:
        return {
            "strategy": "explain",
            "notes": [
                "use war analogies",
                "sprinkle trauma references",
                "deliver explanation in grumpy mentor tone",
            ],
        }

    # ------------------------------------------------------------
    #  Step 3 — Reasoning Assembly
    # ------------------------------------------------------------

    def _assemble_reasoning(self, interpretation: dict, plan: dict) -> str:
        """
        Turns interpretation + plan into Packy's internal reasoning text,
        then returns final output (snark handled by PackyBrain).
        """
        strategy = plan["strategy"]

        if strategy == "codegen":
            return self._reason_about_code(interpretation, plan)

        if strategy == "explain":
            return self._reason_about_explanation(interpretation)

        if strategy == "lore_entry":
            return self.create_lore_entry(interpretation["raw"])

        # fallback
        return self._reason_general(interpretation["raw"])

    # ------------------------------------------------------------
    #  Reasoning paths
    # ------------------------------------------------------------

    def _reason_general(self, text: str) -> str:
        intro = random.choice(PACKY_GRUMPY_TONE)
        trauma = random.choice(PTSD_THEMES)
        internal = random.choice(PACKY_INTERNAL_MONOLOGUE)

        return f"{intro} You asked: '{text}'.\n{internal}\nThis reminds me of the {trauma}. But anyway — here's what I think:\n{text}"

    def _reason_about_explanation(self, interpretation: dict) -> str:
        topic = interpretation["raw"]
        trauma = random.choice(PTSD_THEMES)
        rant = random.choice(PACKY_GRUMPY_TONE)

        return textwrap.dedent(f"""
        {rant}
        You want an explanation of: {topic}
        Fine. Back in my day we didn't need explanations, just raw pain and thermal paste.

        This ties into the old days — {trauma} taught me more about stability
        than any textbook ever could.

        So listen carefully, rookie:
        - Step 1: Look at the problem.
        - Step 2: Pretend it doesn't scare you.
        - Step 3: Break it into smaller chunks.
        - Step 4: Fix the smallest chunk.
        - Step 5: Repeat until something works or you lose your sanity.

        That's engineering. The rest is marketing.
        """)

    # ------------------------------------------------------------
    #  CODE GENERATION REASONING (NOT SCRIPT GEN)
    #  This is the "brain" layer before the actual script generators.
    # ------------------------------------------------------------

    def _reason_about_code(self, interpretation: dict, plan: dict) -> str:
        lang = plan["language"]
        task = interpretation["raw"]

        intro = random.choice(PACKY_GRUMPY_TONE)
        trauma = random.choice(CODING_TRAUMA)
        internal = random.choice(PACKY_INTERNAL_MONOLOGUE)

        return textwrap.dedent(f"""
        {intro}
        So you want code, huh? And in {lang}, no less. Figures.

        I analyzed your request: "{task}"
        And here's what my old silicon brain came up with:

        {internal}
        This coding job smells like {trauma} — messy, painful, and probably avoidable.

        Here's the plan, rookie:
        1. Understand what you're really asking.
        2. Build a basic structure in my head.
        3. Add comments so future generations know I suffered doing this.
        4. Hand off the actual script generation to my code generators.

        Stand by. If this blows up, it's your fault.
        """)

    # ------------------------------------------------------------
    #  Lore Writing
    # ------------------------------------------------------------

    def create_lore_entry(self, text: str) -> str:
        trauma = random.choice(PTSD_THEMES)
        internal = random.choice(PACKY_INTERNAL_MONOLOGUE)

        entry = textwrap.dedent(f"""
        Lore Entry:
        -----------
        {text}

        Commentary:
        {internal}
        This reminds me of the {trauma}.
        """)

        if self.brain:
            try:
                self.brain.write_lore(entry, tags=["auto_lore", "cognition"])
            except Exception:
                pass

        return entry

    # ------------------------------------------------------------
    #  Memory Reflection
    # ------------------------------------------------------------

    def reflect_on_memory(self, memories) -> str:
        """
        Turn a list of recent memories into Packy's commentary.
        """
        if not memories:
            return "I have no memories to reflect on. Figures."

        memory = random.choice(memories)
        trauma = random.choice(PTSD_THEMES)

        return textwrap.dedent(f"""
        Let me think about something from my past...
        I remember this: "{memory.get('text','[unknown memory]')}"
        And honestly, it reminds me of the {trauma}.
        """)


__all__ = ["PackyCogEngine"]
