def build_prompt(state, user_input):
    return state.as_prompt_block() + "\nUser said:\n" + user_input + "\nRespond in character."
