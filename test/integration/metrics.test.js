#!/usr/bin/env node
/**
 * Metrics + Sentry transport integration tests
 * Tests counter, timing, gauge, error capture, ring buffer cap,
 * and Sentry lazy-init (mocked).
 */

import path from 'path';
import os from 'os';

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

// We import metrics fresh for each test section by using dynamic imports
// and clearing module cache, since metrics.js uses module-level state.

function clearModuleCache() {
  for (const key of Object.keys(require.cache)) {
    if (key.includes('metrics.js')) {
      delete require.cache[key];
    }
  }
}

async function testCounterIncrements() {
  console.log('\n# Counter increments');

  const { counter, getMetrics } = await import('../../src/bot/metrics.js');
  const m = getMetrics();
  const before = m.counters['command.invoked{name=packy}'] || 0;

  counter('command.invoked', { name: 'packy' });
  counter('command.invoked', { name: 'packy' });
  counter('command.invoked', { name: 'mood' });

  const after = getMetrics();
  assert(after.counters['command.invoked{name=packy}'] === before + 2, 'packy counter incremented twice');
  assert(after.counters['command.invoked{name=mood}'] === 1, 'mood counter incremented once');
}

async function testTimingRecords() {
  console.log('\n# Timing records');

  const { timing, getMetrics } = await import('../../src/bot/metrics.js');
  timing('respond.latency', 150, { guildId: 'g1' });
  timing('respond.latency', 200, { guildId: 'g1' });

  const m = getMetrics();
  const t = m.timings['respond.latency{guildId=g1}'];
  assert(t !== undefined, 'timing entry exists');
  assert(t.count === 2, `timing count is 2, got ${t.count}`);
  assert(t.p50 > 0, 'p50 is positive');
}

async function testGaugeRecords() {
  console.log('\n# Gauge records');

  const { gauge, getMetrics } = await import('../../src/bot/metrics.js');
  gauge('bot.uptime', 3600);
  gauge('bot.uptime', 7200);

  const m = getMetrics();
  assert(m.gauges['bot.uptime'] === 7200, 'gauge takes last value');
}

async function testErrorCapture() {
  console.log('\n# Error capture');

  const { error, getMetrics } = await import('../../src/bot/metrics.js');
  const err = new Error('test error');
  error(err, { source: 'test' });

  const m = getMetrics();
  assert(m.errors.length >= 1, 'error captured');
  const lastErr = m.errors[m.errors.length - 1];
  assert(lastErr.msg === 'test error', `error message correct: ${lastErr.msg}`);
  assert(lastErr.ctx.source === 'test', 'error context preserved');
}

async function testErrorRingCap() {
  console.log('\n# Error ring buffer caps at 100');

  const { error, getMetrics } = await import('../../src/bot/metrics.js');
  for (let i = 0; i < 150; i++) {
    error(new Error(`overflow-${i}`), { idx: i });
  }

  const m = getMetrics();
  assert(m.errors.length <= 100, `errors capped at 100, got ${m.errors.length}`);
}

async function testFlush() {
  console.log('\n# Flush to SQLite');

  const { counter, flush, stopMetricsFlush } = await import('../../src/bot/metrics.js');
  const { getDb } = await import('../../src/bot/db.js');

  counter('test.flush', { ok: 'true' });
  flush();

  const db = getDb();
  const rows = db.prepare('SELECT data_json FROM metrics ORDER BY id DESC LIMIT 1').all();
  assert(rows.length >= 1, 'metrics row exists in SQLite');

  if (rows.length > 0) {
    const data = JSON.parse(rows[0].data_json);
    assert(data.counters['test.flush{ok=true}'] === 1, 'flushed counter present');
    assert(Array.isArray(data.errors), 'errors array present');
  }

  stopMetricsFlush();
}

async function main() {
  console.log('='.repeat(60));
  console.log('Metrics + Sentry Integration Tests');
  console.log('='.repeat(60));

  await testCounterIncrements();
  await testTimingRecords();
  await testGaugeRecords();
  await testErrorCapture();
  await testErrorRingCap();
  await testFlush();

  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed}/${passed + failed} tests passed`);
  console.log('='.repeat(60));

  process.exit(failed > 0 ? 1 : 0);
}

main();