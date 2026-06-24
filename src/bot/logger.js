/**
 * Structured logger for GargoylePacky
 * Provides log levels, correlation IDs, and formatted output
 */

let _logLevel = process.env.LOG_LEVEL || 'info';
const LOG_LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };

let _correlationCounter = 0;
let _guildCounter = new Map();

export function getCorrelationId(guildId) {
  if (!guildId) return `nocorr-${Date.now()}`;
  if (!_guildCounter.has(guildId)) _guildCounter.set(guildId, 0);
  const seq = ++_guildCounter.get(guildId);
  return `${guildId.slice(-4)}-${seq}`;
}

function formatMessage(level, message, meta = {}) {
  const timestamp = new Date().toISOString();
  const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
  return `[${timestamp}] [${level.toUpperCase()}] ${message}${metaStr}`;
}

function shouldLog(level) {
  return LOG_LEVELS[level] >= LOG_LEVELS[_logLevel];
}

export const logger = {
  debug(message, meta) {
    if (shouldLog('debug')) console.log(formatMessage('debug', message, meta));
  },
  info(message, meta) {
    if (shouldLog('info')) console.info(formatMessage('info', message, meta));
  },
  warn(message, meta) {
    if (shouldLog('warn')) console.warn(formatMessage('warn', message, meta));
  },
  error(message, meta) {
    if (shouldLog('error')) console.error(formatMessage('error', message, meta));
  },
  setLevel(level) {
    if (LOG_LEVELS[level] !== undefined) _logLevel = level;
  }
};

export default logger;