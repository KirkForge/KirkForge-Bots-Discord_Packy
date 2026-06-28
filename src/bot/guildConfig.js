import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { logger } from './logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_FILE = path.join(__dirname, '../../data/guild_config.json');

const DEFAULT_CONFIG = {
  prefix: '!packy',
  allowedChannels: [],    // empty = all channels allowed
  botMuted: false,
  chaosEnabled: true,
  unprovokedEnabled: true,
  maxResponseLength: 1990,
  familyFriendly: false,   // per-guild content filter
};

let configCache = {};

export async function loadGuildConfigs() {
  try {
    const raw = await fs.readFile(CONFIG_FILE, 'utf-8');
    configCache = JSON.parse(raw);
  } catch { /* non-fatal: no config file yet */ 
    configCache = {};
  }
}

export async function saveGuildConfigs() {
  const tmp = CONFIG_FILE + '.tmp';
  await fs.mkdir(path.dirname(CONFIG_FILE), { recursive: true });
  await fs.writeFile(tmp, JSON.stringify(configCache, null, 2), 'utf-8');
  await fs.rename(tmp, CONFIG_FILE);
}

export function getGuildConfig(guildId) {
  return { ...DEFAULT_CONFIG, ...(configCache[guildId] || {}) };
}

export function setGuildConfig(guildId, updates) {
  configCache[guildId] = { ...(configCache[guildId] || {}), ...updates };
}

export function isChannelAllowed(guildId, channelId) {
  const config = getGuildConfig(guildId);
  // Empty allow-list = deny all (opt-in model).
  if (!config.allowedChannels || config.allowedChannels.length === 0) return false;
  return config.allowedChannels.includes(channelId);
}

export function isGuildMuted(guildId) {
  return getGuildConfig(guildId).botMuted === true;
}

let _saveInterval = null;
export function startAutoSave(intervalMs = 5 * 60 * 1000) {
  if (_saveInterval) clearInterval(_saveInterval);
  _saveInterval = setInterval(() => {
    saveGuildConfigs().catch(error => {
      logger.error('Guild config auto-save failed', { error: error.message });
    });
  }, intervalMs);
}

export function stopAutoSave() {
  if (_saveInterval) {
    clearInterval(_saveInterval);
    _saveInterval = null;
  }
}
