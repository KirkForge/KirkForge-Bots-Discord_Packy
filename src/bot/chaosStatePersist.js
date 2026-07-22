// Per-channel chaos state persistence — SQLite-backed
// Stores injection timestamps and target locks in packy_state.db

import { initDb } from './db.js';

const MAX_CHANNELS = 200;

let _db = null;

function db() {
  if (!_db) _db = initDb();
  return _db;
}

export async function loadChaosState() {
  db();
  cleanupExpiredLocks();
}

export async function saveChaosState() {
}

function _getChannelRow(channelId) {
  return db().prepare(
    "SELECT state_json FROM chaos_state WHERE channel_id = ?"
  ).get(channelId);
}

function _setChannelRow(channelId, data) {
  const json = JSON.stringify(data);
  const existing = db().prepare(
    "SELECT guild_id FROM chaos_state WHERE channel_id = ?"
  ).get(channelId);
  if (existing) {
    db().prepare(
      "UPDATE chaos_state SET state_json = ? WHERE channel_id = ?"
    ).run(json, channelId);
  } else {
    db().prepare(
      "INSERT INTO chaos_state (guild_id, channel_id, state_json) VALUES (?, ?, ?)"
    ).run('', channelId, json);
  }
}

export function getLastInjection(channelId) {
  const row = _getChannelRow(channelId);
  if (!row) return null;
  try {
    const data = JSON.parse(row.state_json || '{}');
    return data.lastInjection || null;
  } catch {
    return null;
  }
}

export function setLastInjection(channelId, timestamp) {
  const row = _getChannelRow(channelId);
  let data = {};
  if (row) {
    try { data = JSON.parse(row.state_json || '{}'); } catch { data = {}; }
  }
  data.lastInjection = timestamp;
  _setChannelRow(channelId, data);
  evictIfNeeded();
}

export function getGuildTargetLocks(guildId) {
  const rows = db().prepare(
    "SELECT channel_id, state_json FROM chaos_state WHERE guild_id = ?"
  ).all(guildId);
  const now = Date.now();
  const locks = {};
  for (const row of rows) {
    try {
      const data = JSON.parse(row.state_json || '{}');
      const expiry = data.lockExpiry;
      if (expiry && now <= expiry) {
        const userId = row.channel_id.replace('target_', '');
        locks[userId] = expiry;
      }
    } catch { /* skip malformed */ }
  }
  return locks;
}

export function setTargetLock(guildId, userId, expiry) {
  const json = JSON.stringify({ lockExpiry: expiry });
  db().prepare(
    "INSERT INTO chaos_state (guild_id, channel_id, state_json) VALUES (?, ?, ?) ON CONFLICT(guild_id, channel_id) DO UPDATE SET state_json = excluded.state_json"
  ).run(guildId, `target_${userId}`, json);
}

export function clearTargetLock(guildId, userId) {
  db().prepare(
    "DELETE FROM chaos_state WHERE guild_id = ? AND channel_id = ?"
  ).run(guildId, `target_${userId}`);
}

function evictIfNeeded() {
  const count = db().prepare("SELECT COUNT(*) as cnt FROM chaos_state").get();
  if (count && count.cnt > MAX_CHANNELS * 2) {
    db().prepare(
      "DELETE FROM chaos_state WHERE rowid IN (SELECT rowid FROM chaos_state ORDER BY rowid ASC LIMIT ?)"
    ).run(Math.max(0, count.cnt - MAX_CHANNELS));
  }
}

function cleanupExpiredLocks() {
  const now = Date.now();
  const rows = db().prepare("SELECT guild_id, channel_id, state_json FROM chaos_state").all();
  for (const row of rows) {
    try {
      const data = JSON.parse(row.state_json || '{}');
      if (data.lockExpiry && now > data.lockExpiry) {
        db().prepare(
          "DELETE FROM chaos_state WHERE guild_id = ? AND channel_id = ?"
        ).run(row.guild_id, row.channel_id);
      }
    } catch { /* skip */ }
  }
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