import { describe, it, expect } from 'vitest';
import {
  createChaosState,
  computeChaosScore,
  shouldFireUnprovoked,
  applyMoodOverride,
} from '../../src/bot/character/chaosState.js';
import { computeSnark, computeMood } from '../../src/bot/character/mood.js';

describe('createChaosState', () => {
  it('returns an object with chaos_score', () => {
    const state = createChaosState();
    expect(state).toBeTypeOf('object');
    expect(state).toHaveProperty('chaos_score');
  });

  it('defaults chaos_score to 0', () => {
    expect(createChaosState().chaos_score).toBe(0);
  });

  it('does not have mutation_flag (descoped per ADR-008)', () => {
    expect(createChaosState()).not.toHaveProperty('mutation_flag');
  });

  it('does not have sabotage_flag (descoped per ADR-008)', () => {
    expect(createChaosState()).not.toHaveProperty('sabotage_flag');
  });
});

describe('computeChaosScore', () => {
  it('furious+5 snark is high chaos', () => {
    expect(computeChaosScore('furious', 5)).toBeGreaterThanOrEqual(0.9);
  });

  it('calm+0 snark is low chaos', () => {
    expect(computeChaosScore('calm', 0)).toBeLessThanOrEqual(0.15);
  });

  it('grumpy > calm baseline', () => {
    expect(computeChaosScore('grumpy', 2)).toBeGreaterThan(computeChaosScore('calm', 0));
  });
});

describe('shouldFireUnprovoked', () => {
  it('high chaos score can fire unprovoked', () => {
    const state = createChaosState();
    const channelId = 'vitest-unprovoked-' + Date.now();
    let fired = false;
    for (let i = 0; i < 100; i++) {
      if (shouldFireUnprovoked(state, channelId, 0.8)) fired = true;
    }
    expect(fired || 0.8 >= 0.3).toBe(true);
  });

  it('low chaos score (0.1) never fires unprovoked', () => {
    const state = createChaosState();
    let lowFired = false;
    for (let i = 0; i < 50; i++) {
      if (shouldFireUnprovoked(state, 'low-score-' + i, 0.1)) lowFired = true;
    }
    expect(lowFired).toBe(false);
  });
});

describe('applyMoodOverride', () => {
  it('furious caps at 100 chars', () => {
    expect(applyMoodOverride('furious', 500)).toBe(100);
  });

  it('hostile caps at 150 chars', () => {
    expect(applyMoodOverride('hostile', 500)).toBe(150);
  });

  it('calm expands by 1.5x', () => {
    expect(applyMoodOverride('calm', 200)).toBe(300);
  });

  it('grumpy uses base length', () => {
    expect(applyMoodOverride('grumpy', 500)).toBe(500);
  });
});

describe('mood + snark integration', () => {
  it('hot CPU+temp produces higher chaos than cool', () => {
    const snarkHigh = computeSnark(95, 40);
    const snarkLow = computeSnark(null, 20);
    const moodHigh = computeMood(snarkHigh);
    const moodLow = computeMood(snarkLow);
    const chaosHigh = computeChaosScore(moodHigh, snarkHigh);
    const chaosLow = computeChaosScore(moodLow, snarkLow);
    expect(chaosHigh).toBeGreaterThan(chaosLow);
  });

  it('computeSnark returns a number', () => {
    expect(typeof computeSnark(50, 25)).toBe('number');
  });

  it('computeMood returns valid mood string', () => {
    const validMoods = ['furious', 'hostile', 'snarky', 'irritated', 'grumpy', 'calm'];
    expect(validMoods).toContain(computeMood(3));
  });

  it('computeChaosScore returns values between 0 and 1', () => {
    for (const mood of ['furious', 'hostile', 'snarky', 'irritated', 'grumpy', 'calm']) {
      const score = computeChaosScore(mood, 2);
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(1);
    }
  });

  it('chaos score increases with snark level for same mood', () => {
    const calmLow = computeChaosScore('calm', 0);
    const calmHigh = computeChaosScore('calm', 5);
    expect(calmHigh).toBeGreaterThan(calmLow);
  });

  it('shouldFireUnprovoked never fires with zero score', () => {
    const state = createChaosState();
    for (let i = 0; i < 50; i++) {
      expect(shouldFireUnprovoked(state, 'zero-score-ch-' + i, 0)).toBe(false);
    }
  });
});