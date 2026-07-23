/**
 * SQLite state store for JS-side persistence.
 *
 * Uses node:sqlite (DatabaseSync, built into Node 22+) as primary backend
 * with better-sqlite3 as fallback. Both are synchronous, matching the
 * existing sync call sites (getGuildConfig, getUserState, etc.).
 *
 * If node:sqlite is unavailable, better-sqlite3 is used instead.
 * No --experimental-sqlite flag needed on Node 22+.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import { logger } from './logger.js';

const require = createRequire(import.meta.url);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_DB_PATH = path.join(__dirname, '../../data/packy_state.db');
const MIGRATION_MARKER = path.join(__dirname, '../../data/.migrated_sqlite');

let _db = null;
let _isNodeSqlite = false;

function createConnection(dbPath) {
  try {
    const { DatabaseSync } = require('node:sqlite');
    _isNodeSqlite = true;
    return new DatabaseSync(dbPath);
  } catch {
    try {
      const BetterSqlite3 = require('better-sqlite3');
      _isNodeSqlite = false;
      return new BetterSqlite3(dbPath);
    } catch {
      throw new Error('No SQLite driver available: need node:sqlite (Node 22+) or better-sqlite3');
    }
  }
}

export function getDb(dbPath) {
  if (_db) return _db;
  const resolvedPath = dbPath || process.env.PACKY_DB_PATH || DEFAULT_DB_PATH;
  fs.mkdirSync(path.dirname(resolvedPath), { recursive: true });
  _db = createConnection(resolvedPath);
  _db.exec('PRAGMA journal_mode=WAL');
  _db.exec('PRAGMA synchronous=NORMAL');
  return _db;
}

export function closeDb() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

export function initDb(dbPath) {
  const db = getDb(dbPath);

  db.exec(`
    CREATE TABLE IF NOT EXISTS guild_config (
      guild_id TEXT PRIMARY KEY,
      config_json TEXT NOT NULL DEFAULT '{}'
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS user_state (
      user_id TEXT NOT NULL,
      guild_id TEXT NOT NULL,
      state_json TEXT NOT NULL DEFAULT '{}',
      PRIMARY KEY (user_id, guild_id)
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS chaos_state (
      guild_id TEXT NOT NULL,
      channel_id TEXT NOT NULL,
      state_json TEXT NOT NULL DEFAULT '{}',
      PRIMARY KEY (guild_id, channel_id)
    )
  `);

  migrateFromJson(db);

  const driverName = _isNodeSqlite ? 'node:sqlite' : 'better-sqlite3';
  logger.info('SQLite state store ready', { driver: driverName, migrated: fs.existsSync(MIGRATION_MARKER) });
  return db;
}

function migrateFromJson(db) {
  if (fs.existsSync(MIGRATION_MARKER)) return;

  const dataDir = path.join(__dirname, '../../data');
  let migrated = false;

  const guildFile = path.join(dataDir, 'guild_config.json');
  if (fs.existsSync(guildFile)) {
    try {
      const raw = fs.readFileSync(guildFile, 'utf-8');
      const data = JSON.parse(raw);
      const insertGuild = db.prepare(
        'INSERT OR IGNORE INTO guild_config (guild_id, config_json) VALUES (?, ?)'
      );
      for (const [guildId, config] of Object.entries(data)) {
        insertGuild.run(guildId, JSON.stringify(config));
      }
      migrated = true;
      logger.info('Migrated guild_config.json to SQLite', { count: Object.keys(data).length });
    } catch (e) {
      logger.error('Failed to migrate guild_config.json', { error: e.message });
    }
  }

  const userFile = path.join(dataDir, 'user_state.json');
  if (fs.existsSync(userFile)) {
    try {
      const raw = fs.readFileSync(userFile, 'utf-8');
      const data = JSON.parse(raw);
      const insertUser = db.prepare(
        'INSERT OR IGNORE INTO user_state (user_id, guild_id, state_json) VALUES (?, ?, ?)'
      );
      for (const [key, state] of Object.entries(data)) {
        const parts = key.split(':');
        if (parts.length >= 2) {
          const guildId = parts[0];
          const userId = parts.slice(1).join(':');
          insertUser.run(userId, guildId, JSON.stringify(state));
        }
      }
      migrated = true;
      logger.info('Migrated user_state.json to SQLite');
    } catch (e) {
      logger.error('Failed to migrate user_state.json', { error: e.message });
    }
  }

  const chaosFile = path.join(dataDir, 'chaos_state.json');
  if (fs.existsSync(chaosFile)) {
    try {
      const raw = fs.readFileSync(chaosFile, 'utf-8');
      const data = JSON.parse(raw);
      const channelInjections = data.channelLastInjection || {};
      const insertChaos = db.prepare(
        'INSERT OR IGNORE INTO chaos_state (guild_id, channel_id, state_json) VALUES (?, ?, ?)'
      );
      for (const [channelId, ts] of Object.entries(channelInjections)) {
        insertChaos.run('', channelId, JSON.stringify({ lastInjection: ts }));
      }
      migrated = true;
      logger.info('Migrated chaos_state.json to SQLite');
    } catch (e) {
      logger.error('Failed to migrate chaos_state.json', { error: e.message });
    }
  }

  fs.writeFileSync(MIGRATION_MARKER, migrated ? new Date().toISOString() : 'no-migration-needed', 'utf-8');
}

export function resetForTesting() {
  if (_db) {
    _db.exec('DELETE FROM guild_config');
    _db.exec('DELETE FROM user_state');
    _db.exec('DELETE FROM chaos_state');
    try {
      _db.exec('DELETE FROM metrics');
    } catch {
      // metrics table may not exist yet if flushMetricsToDb hasn't been called
    }
  }
}

/**
 * Read and parse a JSON file from disk.
 * Centralizes all file I/O for static data loading through db.js.
 */
export function readJsonFile(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw);
}

/**
 * Read and parse a JSON file from disk (async).
 * Centralizes all file I/O for static data loading through db.js.
 */
export async function readJsonFileAsync(filePath) {
  const raw = await fs.promises.readFile(filePath, 'utf-8');
  return JSON.parse(raw);
}

/**
 * Flush metrics data to the metrics SQLite table.
 * Replaces the old fs.writeFileSync(metrics.json) persistence.
 */
export function flushMetricsToDb(metricsData) {
  const db = getDb();

  db.exec(`
    CREATE TABLE IF NOT EXISTS metrics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      data_json TEXT NOT NULL,
      flushed_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);

  const insertMetrics = db.prepare('INSERT INTO metrics (data_json) VALUES (?)');
  insertMetrics.run(JSON.stringify(metricsData));

  // Keep only the latest 10 metric snapshots
  db.exec(`DELETE FROM metrics WHERE id NOT IN (SELECT id FROM metrics ORDER BY id DESC LIMIT 10)`);
}