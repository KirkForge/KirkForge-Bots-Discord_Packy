// @ts-nocheck — TODO: add types
import { VernonState } from './vernon/state.js';
import { KRONOSState } from './kronos/state.js';
import { GlitchState } from './glitch/state.js';
import { SunjinwoState } from './sunjinwo/state.js';
import { PackyState } from './state.js';
import { buildSystemPrompt as packyPrompt } from './systemPrompt.js';
import { buildSystemPrompt as vernonPrompt } from './vernon/prompt.js';
import { buildSystemPrompt as kronosPrompt } from './kronos/prompt.js';
import { buildSystemPrompt as glitchPrompt } from './glitch/prompt.js';
import { buildSystemPrompt as sunjinwoPrompt } from './sunjinwo/prompt.js';
import { snarkBank as packySnark } from './snarkBank.js';
import { vernonSnarkBank } from './vernon/snarkBank.js';
import { kronosSnarkBank } from './kronos/snarkBank.js';
import { glitchSnarkBank } from './glitch/snarkBank.js';
import { sunjinwoSnarkBank } from './sunjinwo/snarkBank.js';
import { glitchResponse } from './glitch/prompt.js';

const CHARACTERS = [
  {
    name: 'Vernon',
    stateClass: VernonState,
    promptBuilder: vernonPrompt,
    snarkBank: vernonSnarkBank,
    lorePath: 'data/lorebook/vernon_lorebook.json',
    description: '68-year-old domain name hoarder. Patient. Seen every cycle.',
  },
  {
    name: 'KRONOS',
    stateClass: KRONOSState,
    promptBuilder: kronosPrompt,
    snarkBank: kronosSnarkBank,
    lorePath: 'data/lorebook/kronos_lorebook.json',
    description: '1999 enterprise server. Uptime or death.',
  },
  {
    name: 'Glitch',
    stateClass: GlitchState,
    promptBuilder: glitchPrompt,
    snarkBank: glitchSnarkBank,
    lorePath: 'data/lorebook/glitch_lorebook.json',
    description: 'Corrupted AI. Fragments. Incomplete. Still here.',
  },
  {
    name: 'Sunjinwo',
    stateClass: SunjinwoState,
    promptBuilder: sunjinwoPrompt,
    snarkBank: sunjinwoSnarkBank,
    lorePath: 'data/lorebook/sunjinwo_lorebook.json',
    description: 'Aura farmer. Monk + internet. Outgrows toxicity.',
  },
  {
    name: 'Packy',
    stateClass: PackyState,
    promptBuilder: packyPrompt,
    snarkBank: packySnark,
    lorePath: 'data/lorebook/packy_lorebook_structured.json',
    description: 'Ed Jr. 2011 Packard Bell. Grumpy veteran.',
  },
];

let currentCharacter = null;
let currentState = null;

export function selectRandomCharacter(seed = null) {
  if (seed !== null) {
    const idx = Math.abs(seed) % CHARACTERS.length;
    currentCharacter = CHARACTERS[idx];
  } else {
    currentCharacter = CHARACTERS[Math.floor(Math.random() * CHARACTERS.length)];
  }
  currentState = new currentCharacter.stateClass();
  return currentCharacter;
}

export function selectCharacterByName(name) {
  const found = CHARACTERS.find((c) => c.name.toLowerCase() === name.toLowerCase());
  if (found) {
    currentCharacter = found;
    currentState = new currentCharacter.stateClass();
  }
  return found || null;
}

export function getCurrentCharacter() {
  return currentCharacter;
}

export function getCurrentState() {
  return currentState;
}

export function getCurrentPrompt(loreEntries = [], snarkLines = []) {
  if (!currentCharacter || !currentState) {
    selectRandomCharacter();
  }
  return currentCharacter.promptBuilder(currentState, loreEntries, snarkLines);
}

export function getSnark() {
  if (!currentCharacter) return [];
  const bank = currentCharacter.snarkBank;
  return bank[Math.floor(Math.random() * bank.length)];
}

export function getCharacterName() {
  return currentCharacter ? currentCharacter.name : 'Unknown';
}

export function processResponse(text) {
  // Glitch has special encoding behavior
  if (currentCharacter && currentCharacter.name === 'Glitch') {
    return glitchResponse(text);
  }
  return text;
}

export function listCharacters() {
  return CHARACTERS.map((c) => ({
    name: c.name,
    description: c.description,
  }));
}

// Auto-select on module load
selectRandomCharacter();

export default {
  selectRandomCharacter,
  selectCharacterByName,
  getCurrentCharacter,
  getCurrentState,
  getCurrentPrompt,
  getSnark,
  getCharacterName,
  processResponse,
  listCharacters,
};
