// @ts-nocheck — TODO: add types
// Shared rate limiter — Redis-backed for PM2 cluster mode, in-memory fallback for single process
// Prevents users from bypassing the limit by mixing !packy mentions and /packy slash commands

import { logger } from './logger.js';

const userRateLimits = new Map(); // fallback in-memory
const RATE_LIMIT_WINDOW = 10000; // 10 seconds
const RATE_LIMIT_MAX = 3; // max 3 requests per window

// Redis client (lazy init)
let redisClient = null;
let useRedis = false;

const REDIS_HOST = process.env.REDIS_HOST || 'localhost';
const REDIS_PORT = parseInt(process.env.REDIS_PORT || '6379', 10);
const REDIS_KEY_PREFIX = process.env.REDIS_KEY_PREFIX || 'packy:ratelimit:';

/**
 * Get or create Redis client
 * @returns {Promise<object>|null} Redis client or null if unavailable
 */
async function getRedisClient() {
  if (!useRedis) return null;
  if (redisClient) return redisClient;

  try {
    const { default: Redis } = await import('ioredis');
    redisClient = new Redis({
      host: REDIS_HOST,
      port: REDIS_PORT,
      lazyConnect: true,
      maxRetriesPerRequest: 1,
      connectTimeout: 2000,
    });
    await redisClient.ping();
    return redisClient;
  } catch (error) {
    logger.warn('Redis unavailable, falling back to in-memory rate limiter', {
      error: error.message,
    });
    useRedis = false;
    return null;
  }
}

/**
 * Check if a user is rate limited (Redis mode)
 * Uses INCR + EXPIRE for atomic check-and-set
 * @param {string} userId - Discord user ID
 * @returns {Promise<boolean>} true if rate limited
 */
async function checkRedisRateLimit(userId) {
  const client = await getRedisClient();
  if (!client) return checkMemoryRateLimit(userId);

  const key = `${REDIS_KEY_PREFIX}${userId}`;
  try {
    const count = await client.incr(key);
    if (count === 1) {
      // First request - set expiry
      await client.expire(key, Math.ceil(RATE_LIMIT_WINDOW / 1000));
    }
    return count > RATE_LIMIT_MAX;
  } catch (error) {
    logger.warn('Redis rate limit check failed, falling back', { error: error.message });
    return checkMemoryRateLimit(userId);
  }
}

/**
 * Check if a user is rate limited (memory fallback)
 * @param {string} userId - Discord user ID
 * @returns {boolean} true if rate limited
 */
function checkMemoryRateLimit(userId) {
  const now = Date.now();
  if (!userRateLimits.has(userId)) {
    userRateLimits.set(userId, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return false;
  }

  const limit = userRateLimits.get(userId);
  if (now > limit.resetTime) {
    limit.count = 1;
    limit.resetTime = now + RATE_LIMIT_WINDOW;
    return false;
  }

  limit.count++;
  return limit.count > RATE_LIMIT_MAX;
}

/**
 * Check if a user is rate limited.
 * Uses Redis if REDIS_HOST is configured, falls back to in-memory otherwise.
 * @param {string} userId - Discord user ID
 * @returns {Promise<boolean>} true if rate limited
 */
export async function isRateLimited(userId) {
  if (useRedis) {
    return checkRedisRateLimit(userId);
  }

  // Try to init Redis on first call
  if (process.env.REDIS_HOST || process.env.REDIS_URL) {
    useRedis = true;
    return checkRedisRateLimit(userId);
  }

  // No Redis configured - use memory
  return checkMemoryRateLimit(userId);
}

/**
 * Get current rate limit status for a user (for debugging)
 * @param {string} userId - Discord user ID
 * @returns {Promise<{count: number, remaining: number, resetMs: number}>}
 */
export async function getRateLimitStatus(userId) {
  if (useRedis) {
    const client = await getRedisClient();
    if (client) {
      const key = `${REDIS_KEY_PREFIX}${userId}`;
      try {
        const count = await client.get(key);
        const ttl = await client.ttl(key);
        return {
          count: parseInt(count || '0', 10),
          remaining: Math.max(0, RATE_LIMIT_MAX - parseInt(count || '0', 10)),
          resetMs: (ttl || 0) * 1000,
        };
      } catch {
        /* non-fatal: fall through to memory */
      }
    }
  }

  const now = Date.now();
  const entry = userRateLimits.get(userId);
  if (!entry || now > entry.resetTime) {
    return { count: 0, remaining: RATE_LIMIT_MAX, resetMs: 0 };
  }
  return {
    count: entry.count,
    remaining: Math.max(0, RATE_LIMIT_MAX - entry.count),
    resetMs: entry.resetTime - now,
  };
}

/**
 * Clear rate limit for a user (admin override)
 * @param {string} userId - Discord user ID
 */
export async function clearRateLimit(userId) {
  if (useRedis) {
    const client = await getRedisClient();
    if (client) {
      const key = `${REDIS_KEY_PREFIX}${userId}`;
      await client.del(key).catch(() => {});
    }
  }
  userRateLimits.delete(userId);
}

export default { isRateLimited, getRateLimitStatus, clearRateLimit };
