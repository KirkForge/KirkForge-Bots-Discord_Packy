export function buildPrompt(state, userInput) {
  return state.asPromptBlock() + '\nUser said:\n' + userInput + '\nRespond in character.';
}
