import { describe, it, expect } from 'vitest';

describe('Metrics', () => {
  describe('counter increments', () => {
    it('increments named counter with tags', async () => {
      const { counter, getMetrics } = await import('../../src/bot/metrics.js');
      const m = getMetrics();
      const before = m.counters['command.invoked{name=vitest}'] || 0;
      counter('command.invoked', { name: 'vitest' });
      counter('command.invoked', { name: 'vitest' });
      counter('command.invoked', { name: 'other' });
      const after = getMetrics();
      expect(after.counters['command.invoked{name=vitest}']).toBe(before + 2);
      expect(after.counters['command.invoked{name=other}']).toBe(1);
    });
  });

  describe('timing records', () => {
    it('records timing entries with count and p50', async () => {
      const { timing, getMetrics } = await import('../../src/bot/metrics.js');
      timing('respond.latency', 150, { guildId: 'vitest-g1' });
      timing('respond.latency', 200, { guildId: 'vitest-g1' });
      const m = getMetrics();
      const t = m.timings['respond.latency{guildId=vitest-g1}'];
      expect(t).toBeDefined();
      expect(t.count).toBe(2);
      expect(t.p50).toBeGreaterThan(0);
    });
  });

  describe('gauge records', () => {
    it('takes last value', async () => {
      const { gauge, getMetrics } = await import('../../src/bot/metrics.js');
      gauge('bot.uptime', 3600);
      gauge('bot.uptime', 7200);
      const m = getMetrics();
      expect(m.gauges['bot.uptime']).toBe(7200);
    });
  });

  describe('error capture', () => {
    it('captures error with context', async () => {
      const { error, getMetrics } = await import('../../src/bot/metrics.js');
      const err = new Error('vitest error');
      error(err, { source: 'vitest' });
      const m = getMetrics();
      expect(m.errors.length).toBeGreaterThanOrEqual(1);
      const lastErr = m.errors[m.errors.length - 1];
      expect(lastErr.msg).toBe('vitest error');
      expect(lastErr.ctx.source).toBe('vitest');
    });
  });

  describe('error ring buffer caps at 100', () => {
    it('caps errors at 100', async () => {
      const { error, getMetrics } = await import('../../src/bot/metrics.js');
      for (let i = 0; i < 150; i++) {
        error(new Error(`overflow-${i}`), { idx: i });
      }
      const m = getMetrics();
      expect(m.errors.length).toBeLessThanOrEqual(100);
    });
  });

  describe('flush to SQLite', () => {
    it('flushes metrics to SQLite', async () => {
      const { counter, flush, stopMetricsFlush } = await import('../../src/bot/metrics.js');
      const { getDb } = await import('../../src/bot/db.js');
      counter('test.flush', { ok: 'true' });
      flush();
      const db = getDb();
      const rows = db.prepare('SELECT data_json FROM metrics ORDER BY id DESC LIMIT 1').all();
      expect(rows.length).toBeGreaterThanOrEqual(1);
      if (rows.length > 0) {
        const data = JSON.parse(rows[0].data_json);
        expect(data.counters['test.flush{ok=true}']).toBe(1);
        expect(Array.isArray(data.errors)).toBe(true);
      }
      stopMetricsFlush();
    });
  });

  describe('Sentry lazy-init', () => {
    it('captures error even with Sentry DSN set', async () => {
      const { error, getMetrics, stopMetricsFlush } = await import('../../src/bot/metrics.js');
      const err = new Error('sentry-vitest-test');
      error(err, { source: 'vitest-sentry' });
      const m = getMetrics();
      expect(m.errors.length).toBeGreaterThanOrEqual(1);
      const lastErr = m.errors[m.errors.length - 1];
      expect(lastErr.msg).toBe('sentry-vitest-test');
      stopMetricsFlush();
    });
  });

  describe('counter isolation', () => {
    it('counters with different tags are independent', async () => {
      const { counter, getMetrics } = await import('../../src/bot/metrics.js');
      counter('api.call', { method: 'GET' });
      counter('api.call', { method: 'POST' });
      counter('api.call', { method: 'GET' });
      const m = getMetrics();
      expect(m.counters['api.call{method=GET}']).toBeGreaterThanOrEqual(2);
      expect(m.counters['api.call{method=POST}']).toBeGreaterThanOrEqual(1);
    });
  });

  describe('gauge overwrite', () => {
    it('gauge retains only the last value', async () => {
      const { gauge, getMetrics } = await import('../../src/bot/metrics.js');
      gauge('cpu.percent', 45);
      gauge('cpu.percent', 78);
      gauge('cpu.percent', 92);
      const m = getMetrics();
      expect(m.gauges['cpu.percent']).toBe(92);
    });
  });

  describe('timing aggregation', () => {
    it('timing stores count and percentiles', async () => {
      const { timing, getMetrics } = await import('../../src/bot/metrics.js');
      for (let i = 1; i <= 10; i++) {
        timing('api.latency', i * 10, { endpoint: '/respond' });
      }
      const m = getMetrics();
      const t = m.timings['api.latency{endpoint=/respond}'];
      expect(t).toBeDefined();
      expect(t.count).toBe(10);
      expect(t.p50).toBeGreaterThan(0);
      expect(t.p99).toBeGreaterThanOrEqual(t.p50);
    });
  });
});