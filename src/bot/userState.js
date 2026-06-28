import fs from 'fs/promises';
import path from 'path';
import { logger } from './logger.js';

const STATE_FILE = path.join(process.cwd(), 'data', 'user_state.json');

// In-memory cache
let stateCache = {};

// LRU eviction: track access order and max entries per guild
const MAX_USERS_PER_GUILD = 100;
let accessOrder = []; // guildId:userId ordered oldest→newest

function evictLRU() {
  while (accessOrder.length > 0 && Object.keys(stateCache).length > MAX_USERS_PER_GUILD * 10) {
    const oldest = accessOrder.shift();
    if (stateCache[oldest]) {
      delete stateCache[oldest];
    }
  }
}

function touchKey(key) {
  const idx = accessOrder.indexOf(key);
  if (idx !== -1) accessOrder.splice(idx, 1);
  accessOrder.push(key);
  evictLRU();
}

/**
 * Load state from file into memory cache
 * If file doesn't exist, starts with empty object
 * @returns {Promise<void>}
 */
export async function loadState() {
  try {
    const data = await fs.readFile(STATE_FILE, 'utf-8');
    stateCache = JSON.parse(data);
  } catch (error) {
    if (error.code === 'ENOENT') {
      stateCache = {};
    } else {
      logger.error('Failed to load state', { error: error.message });
      stateCache = {};
    }
  }
}

/**
 * Save state to file atomically (write to .tmp then rename)
 * @returns {Promise<void>}
 */
export async function saveState() {
  try {
    const dir = path.dirname(STATE_FILE);
    await fs.mkdir(dir, { recursive: true });

    const tmpFile = `${STATE_FILE}.tmp`;
    const data = JSON.stringify(stateCache, null, 2);
    await fs.writeFile(tmpFile, data, 'utf-8');
    await fs.rename(tmpFile, STATE_FILE);
  } catch (error) {
    logger.error('Failed to save state', { error: error.message });
  }
}

/**
 * Get state for a specific user in a specific guild
 * @param {string} guildId - Guild/server ID
 * @param {string} userId - User ID
 * @returns {object} User state object with default values
 */
export function getUserState(guildId, userId) {
  const key = `${guildId}:${userId}`;
  if (!stateCache[key]) {
    stateCache[key] = {
      turnCount: 0,
      lastSeen: null,
      interactionCount: 0,
      mood_history: []
    };
  }
  touchKey(key);
  return stateCache[key];
}

/**
 * Update user state with provided updates
 * Automatically increments interactionCount, sets lastSeen, and trims mood_history to last 10
 * Does NOT auto-save (caller must call saveState periodically)
 * @param {string} guildId - Guild/server ID
 * @param {string} userId - User ID
 * @param {object} updates - Fields to merge into state
 * @returns {object} Updated user state
 */
export function updateUserState(guildId, userId, updates = {}) {
  const state = getUserState(guildId, userId);

  // Merge updates
  Object.assign(state, updates);

  // Always increment interaction count
  state.interactionCount = (state.interactionCount || 0) + 1;

  // Always update lastSeen
  state.lastSeen = Date.now();

  // Trim mood_history to last 10 entries
  if (Array.isArray(state.mood_history)) {
    state.mood_history = state.mood_history.slice(-10);
  }

  touchKey(`${guildId}:${userId}`);
  return state;
}

/**
 * Get top N users by interaction count in a guild
 * @param {string} guildId - Guild/server ID
 * @param {number} n - Number of top users to return (default 5)
 * @returns {Array<{userId: string, state: object}>} Top users sorted by interactionCount
 */
export function getTopUsers(guildId, n = 5) {
  const guildUsers = [];

  // Collect all users in this guild
  for (const key of Object.keys(stateCache)) {
    const [keyGuildId, userId] = key.split(':');
    if (keyGuildId === guildId) {
      guildUsers.push({
        userId,
        state: stateCache[key]
      });
    }
  }

  // Sort by interactionCount descending
  guildUsers.sort((a, b) => (b.state.interactionCount || 0) - (a.state.interactionCount || 0));

  // Return top n
  return guildUsers.slice(0, n);
}

// Auto-save interval
let _saveInterval = null;

/**
 * Start auto-saving state periodically
 * @param {number} intervalMs - Interval in milliseconds (default 5 minutes)
 * @returns {void}
 */
export function startAutoSave(intervalMs = 5 * 60 * 1000) {
  if (_saveInterval) {
    clearInterval(_saveInterval);
  }
  _saveInterval = setInterval(() => {
    saveState().catch(error => {
      logger.error('Auto-save failed', { error: error.message });
    });
  }, intervalMs);
}

/**
 * Stop auto-saving state
 * @returns {void}
 */
export function stopAutoSave() {
  if (_saveInterval) {
    clearInterval(_saveInterval);
    _saveInterval = null;
  }
}
