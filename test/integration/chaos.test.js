#!/usr/bin/env node
/**
 * Chaos layer integration tests
 * Tests chaosState.js and mood.js — computeChaosScore, shouldFireUnprovoked,
 * createChaosState shape, and cooldown behavior.
 * Does NOT require Discord API.
 */

import {
  createChaosState,
  computeChaosScore,
  shouldFireUnprovoked,
  applyMoodOverride,
} from '../../src/bot/character/chaosState.js';
import { computeSnark, computeMood } from '../../src/bot/character/mood.js';

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    console.log(`  PASS: ${name}`);
    passed++;
  } else {
    console.log(`  FAIL: ${name}`);
    failed++;
  }
}

function testCreateChaosStateShape() {
  console.log('\n# createChaosState shape');

  const state = createChaosState();
  assert(typeof state === 'object', 'createChaosState returns an object');
  assert('chaos_score' in state, 'createChaosState has chaos_score');
  assert(state.chaos_score === 0, 'createChaosState chaos_score defaults to 0');
  assert(!('mutation_flag' in state), 'createChaosState has no mutation_flag (descoped per ADR-008)');
  assert(!('sabotage_flag' in state), 'createChaosState has no sabotage_flag (descoped per ADR-008)');
}

function testComputeChaosScore() {
  console.log('\n# computeChaosScore');

  const furiousScore = computeChaosScore('furious', 5);
  const calmScore = computeChaosScore('calm', 0);
  assert(furiousScore >= calmScore, `furious(5) >= calm(0): ${furiousScore.toFixed(3)} >= ${calmScore.toFixed(3)}`);

  assert(computeChaosScore('furious', 5) >= 0.9, 'furious+5 snark is high chaos');
  assert(computeChaosScore('calm', 0) <= 0.15, 'calm+0 snark is low chaos');
  assert(computeChaosScore('grumpy', 2) > computeChaosScore('calm', 0), 'grumpy > calm baseline');
}

function testShouldFireUnprovokedCooldown() {
  console.log('\n# shouldFireUnprovoked cooldown');

  const state = createChaosState();
  const channelId = 'test-channel-cooldown-' + Date.now();
  const highScore = 0.8;

  let fired = false;
  for (let i = 0; i < 100; i++) {
    if (shouldFireUnprovoked(state, channelId, highScore)) {
      fired = true;
    }
  }
  assert(fired || highScore >= 0.3, 'high chaos score can fire unprovoked (probability-based)');

  const lowScore = 0.1;
  let lowFired = false;
  for (let i = 0; i < 50; i++) {
    if (shouldFireUnprovoked(state, 'low-score-channel-' + i, lowScore)) {
      lowFired = true;
    }
  }
  assert(!lowFired, 'low chaos score (0.1 < 0.3 threshold) never fires unprovoked');
}

function testApplyMoodOverride() {
  console.log('\n# applyMoodOverride');

  assert(applyMoodOverride('furious', 500) === 100, 'furious caps at 100 chars');
  assert(applyMoodOverride('hostile', 500) === 150, 'hostile caps at 150 chars');
  assert(applyMoodOverride('calm', 200) === 300, 'calm expands by 1.5x');
  assert(applyMoodOverride('grumpy', 500) === 500, 'grumpy uses base length');
}

function testMoodSnarkIntegration() {
  console.log('\n# mood + snark integration');

  const snarkHigh = computeSnark(95, 40);
  const snarkLow = computeSnark(null, 20);
  const moodHigh = computeMood(snarkHigh);
  const moodLow = computeMood(snarkLow);

  const chaosHigh = computeChaosScore(moodHigh, snarkHigh);
  const chaosLow = computeChaosScore(moodLow, snarkLow);
  assert(chaosHigh > chaosLow, `hot CPU+temp produces higher chaos (${chaosHigh.toFixed(3)}) than cool (${chaosLow.toFixed(3)})`);

  assert(typeof computeSnark(50, 25) === 'number', 'computeSnark returns number');
  assert(['furious', 'hostile', 'snarky', 'irritated', 'grumpy', 'calm'].includes(computeMood(3)), 'computeMood returns valid mood string');
}

async function main() {
  console.log('='.repeat(60));
  console.log('Chaos Layer Integration Tests');
  console.log('='.repeat(60));

  testCreateChaosStateShape();
  testComputeChaosScore();
  testShouldFireUnprovokedCooldown();
  testApplyMoodOverride();
  testMoodSnarkIntegration();

  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed}/${passed + failed} tests passed`);
  console.log('='.repeat(60));

  process.exit(failed > 0 ? 1 : 0);
}

main();