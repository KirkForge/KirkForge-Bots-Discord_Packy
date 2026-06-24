// Per-channel chaos state persistence
// Persists channel injection timestamps and target locks to disk
// Uses same atomic-write pattern as userState.js and guildConfig.js

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CHAOS_FILE = path.join(__dirname, '../../data/chaos_state.json');

// In-memory cache
let chaosCache = {
  channelLastInjection: {},  // channelId -> timestamp
  targetLocks: {},           // guildId -> { userId -> expiry }
};

// Eviction to prevent unbounded growth
const MAX_CHANNELS = 200;
const MAX_LOCKS_PER_GUILD = 10;

/**
 * Load chaos state from file into memory cache
 * @returns {Promise<void>}
 */
export async function loadChaosState() {
  try {
    const raw = await fs.readFile(CHAOS_FILE, 'utf-8');
    const parsed = JSON.parse(raw);
    chaosCache.channelLastInjection = parsed.channelLastInjection || {};
    chaosCache.targetLocks = parsed.targetLocks || {};
    
    // Clean up expired locks on load
    cleanupExpiredLocks();
  } catch (error) {
    if (error.code !== 'ENOENT') {
      console.warn('Failed to load chaos state:', error.message);
    }
    chaosCache = { channelLastInjection: {}, targetLocks: {} };
  }
}

/**
 * Save chaos state to file atomically (write to .tmp then rename)
 * @returns {Promise<void>}
 */
export async function saveChaosState() {
  try {
    const dir = path.dirname(CHAOS_FILE);
    await fs.mkdir(dir, { recursive: true });

    // Evict if over limits
    evictIfNeeded();

    const tmpFile = CHAOS_FILE + '.tmp';
    await fs.writeFile(tmpFile, JSON.stringify(chaosCache, null, 2), 'utf-8');
    await fs.rename(tmpFile, CHAOS_FILE);
  } catch (error) {
    console.warn('Failed to save chaos state:', error.message);
  }
}

/**
 * Evict old entries if cache exceeds limits
 */
function evictIfNeeded() {
  // Evict oldest channel entries if over limit
  if (Object.keys(chaosCache.channelLastInjection).length > MAX_CHANNELS) {
    const entries = Object.entries(chaosCache.channelLastInjection)
      .sort((a, b) => a[1] - b[1]);  // oldest first
    const toRemove = entries.slice(0, entries.length - MAX_CHANNELS);
    for (const [chId] of toRemove) {
      delete chaosCache.channelLastInjection[chId];
    }
  }

  // Evict oldest guild lock entries if over limit
  for (const [guildId, locks] of Object.entries(chaosCache.targetLocks)) {
    if (Object.keys(locks).length > MAX_LOCKS_PER_GUILD) {
      const entries = Object.entries(locks).sort((a, b) => a[1] - b[1]);
      const toRemove = entries.slice(0, entries.length - MAX_LOCKS_PER_GUILD);
      for (const [userId] of toRemove) {
        delete chaosCache.targetLocks[guildId][userId];
      }
    }
  }
}

/**
 * Remove expired locks from cache (called on load and periodically)
 */
function cleanupExpiredLocks() {
  const now = Date.now();
  for (const [guildId, locks] of Object.entries(chaosCache.targetLocks)) {
    for (const [userId, expiry] of Object.entries(locks)) {
      if (now > expiry) {
        delete chaosCache.targetLocks[guildId][userId];
      }
    }
    if (Object.keys(chaosCache.targetLocks[guildId]).length === 0) {
      delete chaosCache.targetLocks[guildId];
    }
  }
}

/**
 * Get last injection timestamp for a channel
 * @param {string} channelId - Discord channel ID
 * @returns {number|null} Unix timestamp or null if never injected
 */
export function getLastInjection(channelId) {
  return chaosCache.channelLastInjection[channelId] || null;
}

/**
 * Set last injection timestamp for a channel
 * @param {string} channelId - Discord channel ID
 * @param {number} timestamp - Unix timestamp
 */
export function setLastInjection(channelId, timestamp) {
  chaosCache.channelLastInjection[channelId] = timestamp;
}

/**
 * Get target locks for a guild
 * @param {string} guildId - Discord guild ID
 * @returns {Map<string, number>} Map of userId -> expiry timestamp
 */
export function getGuildTargetLocks(guildId) {
  const locks = chaosCache.targetLocks[guildId] || {};
  // Clean expired from the returned map
  const now = Date.now();
  for (const [userId, expiry] of Object.entries(locks)) {
    if (now > expiry) delete locks[userId];
  }
  return locks;
}

/**
 * Set target lock for a user in a guild
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 * @param {number} expiry - Unix timestamp when lock expires
 */
export function setTargetLock(guildId, userId, expiry) {
  if (!chaosCache.targetLocks[guildId]) {
    chaosCache.targetLocks[guildId] = {};
  }
  chaosCache.targetLocks[guildId][userId] = expiry;
}

/**
 * Clear target lock for a user in a guild
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 */
export function clearTargetLock(guildId, userId) {
  if (chaosCache.targetLocks[guildId]) {
    delete chaosCache.targetLocks[guildId][userId];
  }
}

// Auto-save interval
let _saveInterval = null;

/**
 * Start auto-saving chaos state periodically
 * @param {number} intervalMs - Interval in milliseconds (default 5 minutes)
 */
export function startAutoSave(intervalMs = 5 * 60 * 1000) {
  if (_saveInterval) clearInterval(_saveInterval);
  _saveInterval = setInterval(() => {
    saveChaosState().catch(err => {
      console.warn('Chaos state auto-save failed:', err.message);
    });
  }, intervalMs);
}

/**
 * Stop auto-saving chaos state
 */
export function stopAutoSave() {
  if (_saveInterval) {
    clearInterval(_saveInterval);
    _saveInterval = null;
  }
}

export default {
  loadChaosState,
  saveChaosState,
  getLastInjection,
  setLastInjection,
  getGuildTargetLocks,
  setTargetLock,
  clearTargetLock,
  startAutoSave,
  stopAutoSave,
};