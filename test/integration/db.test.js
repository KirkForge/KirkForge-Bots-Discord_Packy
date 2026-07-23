#!/usr/bin/env node
/**
 * SQLite state store integration tests
 * Tests db.js init, round-trips for guild/user/chaos rows,
 * JSON migration, WAL mode, idempotent migration.
 */

import fs from 'fs';
import path from 'path';
import os from 'os';
import { initDb, getDb, closeDb, resetForTesting, readJsonFile, readJsonFileAsync, flushMetricsToDb } from '../../src/bot/db.js';
import {
  getGuildConfig,
  setGuildConfig,
  isChannelAllowed,
  isGuildMuted,
} from '../../src/bot/guildConfig.js';
import {
  getUserState,
  updateUserState,
} from '../../src/bot/userState.js';
import {
  getLastInjection,
  setLastInjection,
} from '../../src/bot/chaosStatePersist.js';

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

const TMPDIR = fs.mkdtempSync(path.join(os.tmpdir(), 'packy-db-test-'));

function cleanup() {
  try { closeDb(); } catch { /* ignore */ }
  try { fs.rmSync(TMPDIR, { recursive: true }); } catch { /* ignore */ }
}

async function testDbInit() {
  console.log('\n# DB init and WAL mode');

  cleanup();
  const dbPath = path.join(TMPDIR, 'test1.db');
  process.env.PACKY_DB_PATH = dbPath;

  const db = initDb();
  assert(db != null, 'initDb returns a database');

  const row = db.prepare('PRAGMA journal_mode').get();
  assert(row.journal_mode === 'wal', `WAL mode enabled: ${row.journal_mode}`);

  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
  const tableNames = tables.map(t => t.name).sort();
  assert(tableNames.includes('chaos_state'), 'chaos_state table exists');
  assert(tableNames.includes('guild_config'), 'guild_config table exists');
  assert(tableNames.includes('user_state'), 'user_state table exists');

  closeDb();
  delete process.env.PACKY_DB_PATH;
}

async function testGuildRoundTrip() {
  console.log('\n# Guild config round-trip');

  cleanup();
  const dbPath = path.join(TMPDIR, 'test2.db');
  process.env.PACKY_DB_PATH = dbPath;
  initDb();
  resetForTesting();

  setGuildConfig('test-guild-rt', { botMuted: true, location: 'Berlin' });
  const cfg = getGuildConfig('test-guild-rt');
  assert(cfg.botMuted === true, 'botMuted persisted');
  assert(cfg.location === 'Berlin', 'custom field preserved');
  assert(cfg.prefix === '!packy', 'unset fields keep defaults');

  setGuildConfig('test-guild-rt', { chaosEnabled: false });
  const cfg2 = getGuildConfig('test-guild-rt');
  assert(cfg2.botMuted === true, 'first value preserved');
  assert(cfg2.chaosEnabled === false, 'second value merged');

  closeDb();
  delete process.env.PACKY_DB_PATH;
}

async function testUserRoundTrip() {
  console.log('\n# User state round-trip');

  cleanup();
  const dbPath = path.join(TMPDIR, 'test3.db');
  process.env.PACKY_DB_PATH = dbPath;
  initDb();
  resetForTesting();

  const state = getUserState('guild1', 'user1');
  assert(state.turnCount === 0, 'default turnCount is 0');
  assert(state.interactionCount === 0, 'default interactionCount is 0');

  const updated = updateUserState('guild1', 'user1', { turnCount: 5 });
  assert(updated.turnCount === 5, 'turnCount updated to 5');
  assert(updated.interactionCount === 1, 'interactionCount incremented');

  const stateAgain = getUserState('guild1', 'user1');
  assert(stateAgain.turnCount === 5, 'turnCount persists after getUserState');
  assert(stateAgain.interactionCount === 1, 'interactionCount persists');

  closeDb();
  delete process.env.PACKY_DB_PATH;
}

async function testChaosRoundTrip() {
  console.log('\n# Chaos state round-trip');

  cleanup();
  const dbPath = path.join(TMPDIR, 'test4.db');
  process.env.PACKY_DB_PATH = dbPath;
  initDb();
  resetForTesting();

  assert(getLastInjection('ch-1') === null, 'no injection for unknown channel');

  setLastInjection('ch-1', 12345);
  assert(getLastInjection('ch-1') === 12345, 'injection timestamp persisted');

  setLastInjection('ch-1', 67890);
  assert(getLastInjection('ch-1') === 67890, 'injection timestamp updated');

  closeDb();
  delete process.env.PACKY_DB_PATH;
}

async function testMigrationFromJson() {
  console.log('\n# JSON migration');

  cleanup();
  const testDataDir = path.join(TMPDIR, 'data');
  fs.mkdirSync(testDataDir, { recursive: true });

  const guildData = {
    'migrated-guild-1': { botMuted: true, location: 'Paris' },
    'migrated-guild-2': { chaosEnabled: false },
  };
  fs.writeFileSync(path.join(testDataDir, 'guild_config.json'), JSON.stringify(guildData, null, 2));

  const markerPath = path.join(testDataDir, '.migrated_sqlite');
  assert(!fs.existsSync(markerPath), 'marker does not exist before migration');

  const dbPath = path.join(testDataDir, 'packy_state.db');
  process.env.PACKY_DB_PATH = dbPath;

  // Override db.js's data directory reference by creating the expected JSON
  // files in the location db.js expects (../../data/ relative to db.js)
  const realDataDir = path.join(process.cwd(), 'data');
  const realGuildFile = path.join(realDataDir, 'guild_config.json');
  let backupGuildFile = null;
  const realMarker = path.join(realDataDir, '.migrated_sqlite');
  let hadMarker = false;
  let backupMarker = null;

  if (fs.existsSync(realGuildFile)) {
    backupGuildFile = realGuildFile + '.bak_test';
    fs.copyFileSync(realGuildFile, backupGuildFile);
  }
  if (fs.existsSync(realMarker)) {
    hadMarker = true;
    backupMarker = realMarker + '.bak_test';
    fs.copyFileSync(realMarker, backupMarker);
    fs.unlinkSync(realMarker);
  }
  fs.writeFileSync(realGuildFile, JSON.stringify(guildData, null, 2));

  const db = initDb();

  assert(fs.existsSync(realMarker), 'migration marker created');
  const row = db.prepare("SELECT config_json FROM guild_config WHERE guild_id = 'migrated-guild-1'").get();
  const parsed = JSON.parse(row.config_json);
  assert(parsed.botMuted === true, 'migrated guild 1 botMuted persisted');
  assert(parsed.location === 'Paris', 'migrated guild 1 location preserved');

  closeDb();

  // Restore
  if (backupGuildFile) {
    fs.copyFileSync(backupGuildFile, realGuildFile);
    fs.unlinkSync(backupGuildFile);
  } else {
    fs.unlinkSync(realGuildFile);
  }
  if (hadMarker) {
    fs.copyFileSync(backupMarker, realMarker);
    fs.unlinkSync(backupMarker);
  } else if (fs.existsSync(realMarker)) {
    fs.unlinkSync(realMarker);
  }
  delete process.env.PACKY_DB_PATH;
}

async function testMigrationIdempotent() {
  console.log('\n# Migration idempotent (marker prevents re-migration)');

  cleanup();
  const realDataDir = path.join(process.cwd(), 'data');
  const realMarker = path.join(realDataDir, '.migrated_sqlite');
  let hadMarker = false;
  let backupMarker = null;

  if (fs.existsSync(realMarker)) {
    hadMarker = true;
    backupMarker = realMarker + '.bak_test2';
    fs.copyFileSync(realMarker, backupMarker);
  }
  fs.writeFileSync(realMarker, 'previous-migration');

  const dbPath = path.join(TMPDIR, 'idempotent.db');
  process.env.PACKY_DB_PATH = dbPath;
  initDb();

  const db = getDb();
  const count = db.prepare("SELECT COUNT(*) as cnt FROM guild_config").get();
  assert(count.cnt === 0, 'no migration when marker exists');

  closeDb();

  if (hadMarker && backupMarker) {
    fs.copyFileSync(backupMarker, realMarker);
    fs.unlinkSync(backupMarker);
  } else {
    fs.unlinkSync(realMarker);
  }
  delete process.env.PACKY_DB_PATH;
}

async function testReadJsonFile() {
  console.log('\n# readJsonFile reads and parses JSON');

  const tmpFile = path.join(TMPDIR, 'test-read.json');
  const data = { foo: 'bar', num: 42 };
  fs.writeFileSync(tmpFile, JSON.stringify(data));

  const result = readJsonFile(tmpFile);
  assert(result.foo === 'bar', 'readJsonFile parses JSON correctly');
  assert(result.num === 42, 'readJsonFile preserves numbers');

  fs.unlinkSync(tmpFile);
}

async function testReadJsonFileAsync() {
  console.log('\n# readJsonFileAsync reads and parses JSON');

  const tmpFile = path.join(TMPDIR, 'test-read-async.json');
  const data = { async: true, list: [1, 2, 3] };
  fs.writeFileSync(tmpFile, JSON.stringify(data));

  const result = await readJsonFileAsync(tmpFile);
  assert(result.async === true, 'readJsonFileAsync parses JSON correctly');
  assert(result.list.length === 3, 'readJsonFileAsync preserves arrays');

  fs.unlinkSync(tmpFile);
}

async function testFlushMetricsToDb() {
  console.log('\n# flushMetricsToDb writes metrics to SQLite');

  cleanup();
  const dbPath = path.join(TMPDIR, 'test-metrics.db');
  process.env.PACKY_DB_PATH = dbPath;
  initDb();
  resetForTesting();

  const metricsData = { counters: { 'test.metric': 5 }, gauges: {}, timings: {}, errors: [] };
  flushMetricsToDb(metricsData);

  const db = getDb();
  const rows = db.prepare('SELECT data_json FROM metrics ORDER BY id DESC LIMIT 1').all();
  assert(rows.length === 1, 'metrics row inserted');
  const parsed = JSON.parse(rows[0].data_json);
  assert(parsed.counters['test.metric'] === 5, 'metrics data round-trips');

  closeDb();
  delete process.env.PACKY_DB_PATH;
}

async function main() {
  console.log('='.repeat(60));
  console.log('SQLite State Store Integration Tests');
  console.log('='.repeat(60));

  await testDbInit();
  await testGuildRoundTrip();
  await testUserRoundTrip();
  await testChaosRoundTrip();
  await testMigrationFromJson();
  await testMigrationIdempotent();
  await testReadJsonFile();
  await testReadJsonFileAsync();
  await testFlushMetricsToDb();

  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed}/${passed + failed} tests passed`);
  console.log('='.repeat(60));

  process.exit(failed > 0 ? 1 : 0);
}

main();