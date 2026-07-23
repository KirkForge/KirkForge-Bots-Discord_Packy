import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import {
  initDb,
  getDb,
  closeDb,
  resetForTesting,
  readJsonFile,
  readJsonFileAsync,
  flushMetricsToDb,
} from '../../src/bot/db.js';
import {
  getGuildConfig,
  setGuildConfig,
  isChannelAllowed,
  isGuildMuted,
} from '../../src/bot/guildConfig.js';
import { getUserState, updateUserState } from '../../src/bot/userState.js';
import { getLastInjection, setLastInjection } from '../../src/bot/chaosStatePersist.js';

const TMPDIR = fs.mkdtempSync(path.join(os.tmpdir(), 'packy-db-vitest-'));

describe('DB init and WAL mode', () => {
  afterEach(() => {
    closeDb();
    delete process.env.PACKY_DB_PATH;
  });

  it('initDb returns a database', () => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-init.db');
    const db = initDb();
    expect(db).toBeTruthy();
  });

  it('WAL mode is enabled', () => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-wal.db');
    const db = initDb();
    const row = db.prepare('PRAGMA journal_mode').get();
    expect(row.journal_mode).toBe('wal');
  });

  it('creates expected tables', () => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-tables.db');
    const db = initDb();
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
    const tableNames = tables.map((t) => t.name).sort();
    expect(tableNames).toContain('chaos_state');
    expect(tableNames).toContain('guild_config');
    expect(tableNames).toContain('user_state');
  });
});

describe('Guild config round-trip', () => {
  beforeEach(() => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-guild-rt.db');
    initDb();
    resetForTesting();
  });

  it('persists config with custom fields', () => {
    setGuildConfig('vitest-guild-rt', { botMuted: true, location: 'Berlin' });
    const cfg = getGuildConfig('vitest-guild-rt');
    expect(cfg.botMuted).toBe(true);
    expect(cfg.location).toBe('Berlin');
    expect(cfg.prefix).toBe('!packy');
  });

  it('merges partial updates', () => {
    resetForTesting();
    setGuildConfig('vitest-guild-merge', { chaosEnabled: false });
    setGuildConfig('vitest-guild-merge', { familyFriendly: true });
    const cfg = getGuildConfig('vitest-guild-merge');
    expect(cfg.chaosEnabled).toBe(false);
    expect(cfg.familyFriendly).toBe(true);
  });
});

describe('User state round-trip', () => {
  beforeEach(() => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-user-rt.db');
    initDb();
    resetForTesting();
  });

  it('defaults to 0 for counters', () => {
    const state = getUserState('guild1', 'user1');
    expect(state.turnCount).toBe(0);
    expect(state.interactionCount).toBe(0);
  });

  it('updates and persists state', () => {
    resetForTesting();
    const updated = updateUserState('guild1', 'user1', { turnCount: 5 });
    expect(updated.turnCount).toBe(5);
    expect(updated.interactionCount).toBe(1);
  });
});

describe('Chaos state round-trip', () => {
  beforeEach(() => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-chaos-rt.db');
    initDb();
    resetForTesting();
  });

  it('returns null for unknown channel', () => {
    expect(getLastInjection('ch-unknown')).toBeNull();
  });

  it('persists and updates injection timestamp', () => {
    resetForTesting();
    setLastInjection('ch-1', 12345);
    expect(getLastInjection('ch-1')).toBe(12345);
    setLastInjection('ch-1', 67890);
    expect(getLastInjection('ch-1')).toBe(67890);
  });
});

describe('readJsonFile', () => {
  it('reads and parses JSON', () => {
    const tmpFile = path.join(TMPDIR, 'vitest-read.json');
    const data = { foo: 'bar', num: 42 };
    fs.writeFileSync(tmpFile, JSON.stringify(data));
    const result = readJsonFile(tmpFile);
    expect(result.foo).toBe('bar');
    expect(result.num).toBe(42);
    fs.unlinkSync(tmpFile);
  });
});

describe('readJsonFileAsync', () => {
  it('reads and parses JSON asynchronously', async () => {
    const tmpFile = path.join(TMPDIR, 'vitest-read-async.json');
    const data = { async: true, list: [1, 2, 3] };
    fs.writeFileSync(tmpFile, JSON.stringify(data));
    const result = await readJsonFileAsync(tmpFile);
    expect(result.async).toBe(true);
    expect(result.list).toHaveLength(3);
    fs.unlinkSync(tmpFile);
  });
});

describe('flushMetricsToDb', () => {
  beforeEach(() => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-metrics.db');
    initDb();
    resetForTesting();
  });

  it('writes metrics to SQLite', () => {
    const metricsData = { counters: { 'test.metric': 5 }, gauges: {}, timings: {}, errors: [] };
    flushMetricsToDb(metricsData);
    const db = getDb();
    const rows = db.prepare('SELECT data_json FROM metrics ORDER BY id DESC LIMIT 1').all();
    expect(rows).toHaveLength(1);
    const parsed = JSON.parse(rows[0].data_json);
    expect(parsed.counters['test.metric']).toBe(5);
  });
});

describe('Concurrent writes', () => {
  beforeEach(() => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-concurrent.db');
    initDb();
    resetForTesting();
  });

  it('handles multiple setGuildConfig calls without data loss', () => {
    for (let i = 0; i < 10; i++) {
      setGuildConfig(`concurrent-guild-${i}`, { botMuted: i % 2 === 0, turnCount: i });
    }
    for (let i = 0; i < 10; i++) {
      const cfg = getGuildConfig(`concurrent-guild-${i}`);
      expect(cfg.botMuted).toBe(i % 2 === 0);
    }
  });
});

describe('Migration from empty (no JSON files)', () => {
  it('creates tables even without JSON migration', () => {
    process.env.PACKY_DB_PATH = path.join(TMPDIR, 'vitest-empty-migration.db');
    const db = initDb();
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
    const tableNames = tables.map((t) => t.name);
    expect(tableNames).toContain('guild_config');
    expect(tableNames).toContain('user_state');
    expect(tableNames).toContain('chaos_state');
    closeDb();
    delete process.env.PACKY_DB_PATH;
  });
});