// @ts-nocheck — TODO: add types
// Controlled Chaos Layer - implements non-deterministic behavior under strict guardrails
// Per ADR-008: Controlled Chaos Layer

// Note: state is now persisted via chaosStatePersist.js
// Import helpers from persist module
import {
  getLastInjection,
  setLastInjection,
  getGuildTargetLocks,
  setTargetLock,
} from '../chaosStatePersist.js';

/**
 * Creates a new chaos state object for a given interaction
 * @returns {Object} Initial chaos state with all flags zeroed
 */
export function createChaosState() {
  return {
    chaos_score: 0, // float 0-1, derived from mood and snark
  };
}

/**
 * Computes chaos score from mood and snark level
 * Maps mood intensity and snark to a 0-1 float
 * @param {string} mood - Mood string: 'furious', 'hostile', 'snarky', 'irritated', 'grumpy', 'calm'
 * @param {number} snarkLevel - Snark intensity 0-5
 * @returns {number} Chaos score 0-1 (higher = more chaotic)
 */
export function computeChaosScore(mood, snarkLevel) {
  const snarkFactor = Math.min(snarkLevel / 5, 1);
  const moodChaos = {
    furious: 1.0,
    hostile: 0.8,
    snarky: 0.6,
    irritated: 0.5,
    grumpy: 0.4,
    calm: 0.1,
  };
  const baseChaos = moodChaos[mood] || 0.5;
  const combined = baseChaos * 0.6 + snarkFactor * 0.4;
  return Math.min(combined, 1.0);
}

/**
 * Determines whether Packy should fire unprovoked commentary
 * Uses persisted timestamps for cooldown tracking
 * @param {Object} chaosState - Current chaos state
 * @param {string} channelId - Discord channel ID
 * @param {number} chaosScore - Computed chaos score 0-1
 * @returns {boolean} Whether to inject unprovoked commentary
 */
export function shouldFireUnprovoked(chaosState, channelId, chaosScore) {
  if (chaosScore < 0.3) {
    return false;
  }

  const now = Date.now();
  const lastInj = getLastInjection(channelId) || 0;
  const timeSinceLastInjection = now - lastInj;

  const MIN_INJECTION_COOLDOWN = 180000; // 3 minutes
  if (timeSinceLastInjection < MIN_INJECTION_COOLDOWN) {
    return false;
  }

  const injectionProbability = chaosScore * 0.15;
  return Math.random() < injectionProbability;
}

/**
 * Applies mood-based response length overrides
 * @param {string} mood - Current mood
 * @param {number} baseMaxChars - Default max response length
 * @returns {number} Adjusted max character limit
 */
export function applyMoodOverride(mood, baseMaxChars) {
  if (mood === 'furious') return 100;
  if (mood === 'hostile') return 150;
  if (mood === 'calm') return Math.floor(baseMaxChars * 1.5);
  return baseMaxChars;
}

/**
 * Attempts to acquire a target lock on a user
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 * @param {number} interactionCount - Number of interactions with this user this session
 * @returns {boolean} Whether target lock was successfully acquired
 */
export function acquireTargetLock(guildId, userId, interactionCount) {
  if (interactionCount < 3) {
    return false;
  }
  if (Math.random() > 0.05) {
    return false;
  }
  const lockDurationMs = (5 + Math.random() * 15) * 60 * 1000;
  const lockExpiry = Date.now() + lockDurationMs;
  setTargetLock(guildId, userId, lockExpiry);
  return true;
}

/**
 * Checks if a user is currently under target lock
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 * @returns {boolean} True if user is currently locked
 */
export function checkTargetLock(guildId, userId) {
  const locks = getGuildTargetLocks(guildId);
  return !!locks[userId];
}

/**
 * Records an unprovoked injection event for cooldown tracking
 * Persists to disk via chaosStatePersist
 * @param {string} channelId - Discord channel ID
 */
export function recordInjection(channelId) {
  setLastInjection(channelId, Date.now());
}

/**
 * Clears all chaos state (useful for testing or guild reset)
 */
export function _clearAllChaosState() {
  // Import dynamically to avoid circular
  import('./chaosStatePersist.js').then((m) => {
    m.saveChaosState();
  });
}

export default {
  createChaosState,
  computeChaosScore,
  shouldFireUnprovoked,
  applyMoodOverride,
  acquireTargetLock,
  checkTargetLock,
  recordInjection,
  _clearAllChaosState,
};
