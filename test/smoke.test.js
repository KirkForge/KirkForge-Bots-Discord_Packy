import { describe, it, expect } from 'vitest';
import { listCharacters, selectCharacterByName, getCurrentCharacter, getCurrentState } from '../src/bot/character/randomizer.js';
import { loadChaosState, getLastInjection, setLastInjection } from '../src/bot/chaosStatePersist.js';
import { createChaosState, computeChaosScore } from '../src/bot/character/chaosState.js';
import { filterFamilyFriendly } from '../src/bot/character/contentFilter.js';

describe('Characters', () => {
  it('list returns 5 characters', () => {
    expect(listCharacters()).toHaveLength(5);
  });

  it('can select by name', () => {
    const char = selectCharacterByName('Vernon');
    expect(char).toBeTruthy();
    expect(char.name).toBe('Vernon');
  });

  it('getCurrentCharacter works', () => {
    expect(getCurrentCharacter()).toBeTruthy();
  });

  it('getCurrentState works', () => {
    expect(getCurrentState()).toBeTruthy();
  });
});

describe('Chaos', () => {
  it('load empty state', async () => {
    await loadChaosState();
  });

  it('set/get last injection', () => {
    setLastInjection('test-channel-vitest', Date.now());
    const ts = getLastInjection('test-channel-vitest');
    expect(ts).toBeTruthy();
  });

  it('createChaosState works', () => {
    const state = createChaosState();
    expect(typeof state.chaos_score).toBe('number');
  });

  it('computeChaosScore works', () => {
    const score = computeChaosScore('snarky', 3.5);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1);
  });
});

describe('ContentFilter', () => {
  it('basic substitutions work', () => {
    const result = filterFamilyFriendly('I have 47 fragments of that memory', 'Glitch');
    expect(result).not.toContain('47');
  });

  it('blocked words are censored', () => {
    const result = filterFamilyFriendly('You are being an idiot', 'Packy');
    expect(result).not.toContain('idiot');
    expect(result).toContain('not smart');
  });

  it('meatbag replacement works', () => {
    const result = filterFamilyFriendly('Slow down meatbag', 'Packy');
    expect(result).not.toContain('meatbag');
  });
});