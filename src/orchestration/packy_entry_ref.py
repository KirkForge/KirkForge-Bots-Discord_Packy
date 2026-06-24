import os
from layer.orchestrator import Orchestrator
from layer.prompt import build_prompt
from layer.llama_adapter import call_llama

from packy_brain import PackyBrain
from packy_persona import PACKY_CORE_IDENTITY

# init
orch = Orchestrator(
    api_key=os.getenv("OPENWEATHER_API_KEY"),
    location=os.getenv("PACKY_LOCATION", "London")
)

brain = PackyBrain()

print("Packy online. SSH session active. Ctrl+C to exit.\n")

while True:
    try:
        user = input("> ")

        # layer step
        state = orch.step(user)

        # cognition
        cognition = brain.cog.think(user)

        # lore selection
        lore_block = brain.select_lore(
            text=user,
            snark_level=state.snark,
            mood=state.mood
        )

        # build prompt
        prompt = build_prompt(
            state=state,
            persona=PACKY_CORE_IDENTITY,
            lore_block=lore_block,
            cognition=cognition,
            user_input=user
        )

        # call model
        raw_response = call_llama(prompt)

        # personality filter
        final = brain.personality_filter(
            raw_response,
            snark_level=state.snark
        )

        print(final)
        print(
            f"[snark={state.snark:.1f}/5 | cpu={state.cpu:.0f}% | "
            f"temp={state.temp}°C | weather={state.weather}]"
        )

    except KeyboardInterrupt:
        print("\nPacky powering down.")
        break
