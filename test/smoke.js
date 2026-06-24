/**
 * Smoke test for GargoylePacky V2
 * Verifies all core modules can be imported without crashing
 * Run: node test/smoke.js
 */

import { listCharacters, selectCharacterByName, getCurrentCharacter, getCurrentState } from '../src/bot/character/randomizer.js';
import { loadChaosState, getLastInjection, setLastInjection } from '../src/bot/chaosStatePersist.js';
import { createChaosState, computeChaosScore } from '../src/bot/character/chaosState.js';
import { logger } from '../src/bot/logger.js';
import { filterFamilyFriendly } from '../src/bot/character/contentFilter.js';

let errors = [];

function test(name, fn) {
  try {
    fn();
    console.log(`✓ ${name}`);
  } catch (e) {
    console.error(`✗ ${name}: ${e.message}`);
    errors.push({ name, error: e });
  }
}

async function run() {
  console.log('\n=== GargoylePacky V2 Smoke Test ===\n');

  // Test character system
  test('Characters: list returns 5', () => {
    const chars = listCharacters();
    if (chars.length !== 5) throw new Error(`Expected 5, got ${chars.length}`);
  });

  test('Characters: can select by name', () => {
    const char = selectCharacterByName('Vernon');
    if (!char) throw new Error('Failed to select Vernon');
    if (char.name !== 'Vernon') throw new Error(`Wrong name: ${char.name}`);
  });

  test('Characters: getCurrentCharacter works', () => {
    const char = getCurrentCharacter();
    if (!char) throw new Error('No current character');
  });

  test('Characters: getCurrentState works', () => {
    const state = getCurrentState();
    if (!state) throw new Error('No current state');
  });

  // Test chaos state persistence
  test('Chaos: load empty state', async () => {
    await loadChaosState();
  });

  test('Chaos: set/get last injection', () => {
    setLastInjection('test-channel-123', Date.now());
    const ts = getLastInjection('test-channel-123');
    if (!ts) throw new Error('Injection timestamp not set');
  });

  test('Chaos: createChaosState works', () => {
    const state = createChaosState();
    if (typeof state.chaos_score !== 'number') throw new Error('Missing chaos_score');
  });

  test('Chaos: computeChaosScore works', () => {
    const score = computeChaosScore('snarky', 3.5);
    if (score < 0 || score > 1) throw new Error(`Invalid score: ${score}`);
  });

  // Test rate limiter
  test('RateLimiter: memory fallback works', async () => {
    const { isRateLimited, clearRateLimit } = await import('../src/bot/rateLimiter.js');
    // Should not be rate limited on first call
    const result = await isRateLimited('test-user-123');
    if (result !== false) throw new Error('First call should not be rate limited');
    await clearRateLimit('test-user-123');
  });

  test('RateLimiter: no Redis env means memory mode', async () => {
    // Without REDIS_HOST set, useRedis stays false
    const { getRateLimitStatus } = await import('../src/bot/rateLimiter.js');
    const status = await getRateLimitStatus('test-user-456');
    if (typeof status.count !== 'number') throw new Error('Should return count');
    if (typeof status.remaining !== 'number') throw new Error('Should return remaining');
  });

  // Test logger
  test('Logger: setLevel works', () => {
    logger.setLevel('debug');
  });

  // Test bot entrypoint imports without error
  test('Bot index.js: entrypoint loads', async () => {
    // Non-blocking — index.js starts Discord connection which needs a token
    await import('../src/bot/index.js').catch((e) => {
      // Expected: ConfigError or similar without DISCORD_TOKEN
      if (!e.message.includes('DISCORD_TOKEN') && !e.message.includes('token')) {
        errors.push({ name: 'Bot index.js: entrypoint loads', error: new Error(e.message) });
      }
    });
  });

  // Test content filter
  test('ContentFilter: basic substitutions work', () => {
    const result = filterFamilyFriendly('I have 47 fragments of that memory', 'Glitch');
    if (result.includes('47')) throw new Error('Should replace number pattern');
  });

  test('ContentFilter: blocked words are censored', () => {
    const result = filterFamilyFriendly('You are being an idiot', 'Packy');
    if (result.includes('idiot')) throw new Error('idiot should be replaced');
    if (!result.includes('not smart')) throw new Error('Should be replaced with "not smart"');
  });

  test('ContentFilter: meatbag replacement works', () => {
    const result = filterFamilyFriendly('Slow down meatbag', 'Packy');
    if (result.includes('meatbag')) throw new Error('meatbag should be replaced');
  });

  // Summary
  console.log('\n=== Results ===');
  if (errors.length === 0) {
    console.log('All tests passed! ✓\n');
    process.exit(0);
  } else {
    console.error(`${errors.length} test(s) failed:\n`);
    for (const { name, error } of errors) {
      console.error(`  - ${name}: ${error.message}`);
    }
    console.log();
    process.exit(1);
  }
}

run().catch(e => {
  console.error('Test runner error:', e);
  process.exit(1);
});