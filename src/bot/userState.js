// @ts-nocheck — TODO: add types
import { initDb } from './db.js';

let _db = null;

function db() {
  if (!_db) _db = initDb();
  return _db;
}

export async function loadState() {
  db();
}

export async function saveState() {}

export function getUserState(guildId, userId) {
  const row = db()
    .prepare('SELECT state_json FROM user_state WHERE guild_id = ? AND user_id = ?')
    .get(guildId, userId);

  const defaults = { turnCount: 0, lastSeen: null, interactionCount: 0, mood_history: [] };

  if (!row) return defaults;
  try {
    return { ...defaults, ...JSON.parse(row.state_json || '{}') };
  } catch {
    return defaults;
  }
}

export function updateUserState(guildId, userId, updates = {}) {
  const existing = getUserState(guildId, userId);
  const merged = { ...existing, ...updates };
  merged.interactionCount = (merged.interactionCount || 0) + 1;
  merged.lastSeen = Date.now();
  if (Array.isArray(merged.mood_history)) {
    merged.mood_history = merged.mood_history.slice(-10);
  }
  db()
    .prepare(
      'INSERT INTO user_state (user_id, guild_id, state_json) VALUES (?, ?, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET state_json = excluded.state_json',
    )
    .run(userId, guildId, JSON.stringify(merged));
  return merged;
}

export function getTopUsers(guildId, n = 5) {
  const rows = db()
    .prepare('SELECT user_id, state_json FROM user_state WHERE guild_id = ?')
    .all(guildId);

  const users = rows
    .map((row) => {
      try {
        const state = JSON.parse(row.state_json || '{}');
        return { userId: row.user_id, state };
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  users.sort((a, b) => (b.state.interactionCount || 0) - (a.state.interactionCount || 0));
  return users.slice(0, n);
}

let _saveInterval = null;

export function startAutoSave(_intervalMs = 5 * 60 * 1000) {
  if (_saveInterval) clearInterval(_saveInterval);
}

export function stopAutoSave() {
  if (_saveInterval) {
    clearInterval(_saveInterval);
    _saveInterval = null;
  }
}
