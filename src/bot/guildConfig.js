import { initDb } from './db.js';

const DEFAULT_CONFIG = {
  prefix: '!packy',
  allowedChannels: [],
  botMuted: false,
  chaosEnabled: true,
  unprovokedEnabled: true,
  maxResponseLength: 1990,
  familyFriendly: false,
};

let _db = null;

function db() {
  if (!_db) _db = initDb();
  return _db;
}

export async function loadGuildConfigs() {
  db();
}

export async function saveGuildConfigs() {
}

export function getGuildConfig(guildId) {
  const row = db().prepare('SELECT config_json FROM guild_config WHERE guild_id = ?').get(guildId);
  if (!row) return { ...DEFAULT_CONFIG };
  try {
    return { ...DEFAULT_CONFIG, ...JSON.parse(row.config_json || '{}') };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export function setGuildConfig(guildId, updates) {
  const existing = getGuildConfig(guildId);
  const merged = { ...existing, ...updates };
  db().prepare(
    'INSERT INTO guild_config (guild_id, config_json) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET config_json = excluded.config_json'
  ).run(guildId, JSON.stringify(merged));
}

export function isChannelAllowed(guildId, channelId) {
  const config = getGuildConfig(guildId);
  if (!config.allowedChannels || config.allowedChannels.length === 0) return false;
  return config.allowedChannels.includes(channelId);
}

export function isGuildMuted(guildId) {
  return getGuildConfig(guildId).botMuted === true;
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