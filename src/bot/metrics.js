/**
 * Metrics interface for observability.
 *
 * Default transport: in-memory ring buffer flushed to SQLite (data/packy_state.db)
 * every 60s. If SENTRY_DSN is set, errors are also sent to Sentry.
 *
 * Clean-clone safe: no SENTRY_DSN = ring buffer only (zero deps beyond db.js).
 */

import { flushMetricsToDb } from './db.js';
import { logger } from './logger.js';

const MAX_ERRORS = 100;

const counters = new Map();
const gauges = new Map();
const timings = new Map();
const errors = [];
let _sentry = null;
let _sentryInitAttempted = false;
let _flushInterval = null;

function getSentry() {
  if (_sentry === null && !_sentryInitAttempted && process.env.SENTRY_DSN) {
    _sentryInitAttempted = true;
    try {
      const Sentry = await_import_sentry();
      if (Sentry) {
        Sentry.init({ dsn: process.env.SENTRY_DSN, tracesSampleRate: 0 });
        _sentry = Sentry;
      }
    } catch {
      _sentry = null;
    }
  }
  return _sentry;
}

function await_import_sentry() {
  try {
    return require('@sentry/node');
  } catch {
    return null;
  }
}

function key(name, labels) {
  if (!labels || Object.keys(labels).length === 0) return name;
  const parts = Object.entries(labels)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${k}=${v}`)
    .join(',');
  return parts ? `${name}{${parts}}` : name;
}

export function counter(name, labels = {}) {
  const k = key(name, labels);
  counters.set(k, (counters.get(k) || 0) + 1);
}

export function gauge(name, value, labels = {}) {
  const k = key(name, labels);
  gauges.set(k, value);
}

export function timing(name, ms, labels = {}) {
  const k = key(name, labels);
  if (!timings.has(k)) timings.set(k, []);
  const arr = timings.get(k);
  arr.push(ms);
  if (arr.length > 1000) arr.splice(0, arr.length - 1000);
}

export function error(err, context = {}) {
  const entry = {
    ts: new Date().toISOString(),
    msg: err instanceof Error ? err.message : String(err),
    ctx: context,
  };
  errors.push(entry);
  if (errors.length > MAX_ERRORS) errors.splice(0, errors.length - MAX_ERRORS);

  const Sentry = getSentry();
  if (Sentry && err instanceof Error) {
    Sentry.captureException(err, { extra: context });
  }
}

export function getMetrics() {
  return {
    counters: Object.fromEntries(counters),
    gauges: Object.fromEntries(gauges),
    timings: Object.fromEntries(
      [...timings.entries()].map(([k, arr]) => [k, { count: arr.length, p50: percentile(arr, 50), p99: percentile(arr, 99) }])
    ),
    errors: errors.slice(-MAX_ERRORS),
  };
}

function percentile(arr, p) {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

export function flush() {
  try {
    flushMetricsToDb(getMetrics());
  } catch (e) {
    logger.warn('Failed to flush metrics to SQLite', { error: e.message });
  }
}

export function startMetricsFlush(intervalMs = 60 * 1000) {
  if (_flushInterval) clearInterval(_flushInterval);
  _flushInterval = setInterval(flush, intervalMs);
}

export function stopMetricsFlush() {
  if (_flushInterval) {
    clearInterval(_flushInterval);
    _flushInterval = null;
  }
  flush();
}