import { describe, it, expect, beforeEach } from 'vitest';
import { isRateLimited, clearRateLimit, getRateLimitStatus } from '../../src/bot/rateLimiter.js';

describe('RateLimiter', () => {
  describe('sequential limiting', () => {
    const userId = 'vitest-user-seq';

    beforeEach(async () => {
      await clearRateLimit(userId);
    });

    it('first 3 requests are not rate limited', async () => {
      expect(await isRateLimited(userId)).toBe(false);
      expect(await isRateLimited(userId)).toBe(false);
      expect(await isRateLimited(userId)).toBe(false);
    });

    it('4th request is rate limited', async () => {
      await isRateLimited(userId);
      await isRateLimited(userId);
      await isRateLimited(userId);
      expect(await isRateLimited(userId)).toBe(true);
    });

    it('remaining is 0 after exhausting limit', async () => {
      await isRateLimited(userId);
      await isRateLimited(userId);
      await isRateLimited(userId);
      const status = await getRateLimitStatus(userId);
      expect(status.remaining).toBe(0);
    });

    it('clears rate limit', async () => {
      await isRateLimited(userId);
      await isRateLimited(userId);
      await isRateLimited(userId);
      await clearRateLimit(userId);
      expect(await isRateLimited(userId)).toBe(false);
    });
  });

  describe('concurrent limiting', () => {
    it('at most 3 of 6 concurrent requests succeed', async () => {
      const uid = 'vitest-user-conc';
      await clearRateLimit(uid);
      const results = await Promise.all([
        isRateLimited(uid),
        isRateLimited(uid),
        isRateLimited(uid),
        isRateLimited(uid),
        isRateLimited(uid),
        isRateLimited(uid),
      ]);
      const allowed = results.filter((r) => r === false).length;
      const limited = results.filter((r) => r === true).length;
      expect(allowed).toBeLessThanOrEqual(3);
      expect(limited).toBeGreaterThanOrEqual(3);
      expect(allowed + limited).toBe(6);
    });
  });

  describe('per-user isolation', () => {
    it('user A limit does not affect user B', async () => {
      const userA = 'vitest-user-a';
      const userB = 'vitest-user-b';
      await clearRateLimit(userA);
      await clearRateLimit(userB);

      await isRateLimited(userA);
      await isRateLimited(userA);
      await isRateLimited(userA);
      expect(await isRateLimited(userA)).toBe(true);

      expect(await isRateLimited(userB)).toBe(false);
      expect(await isRateLimited(userB)).toBe(false);
      expect(await isRateLimited(userB)).toBe(false);

      expect(await isRateLimited(userA)).toBe(true);

      await clearRateLimit(userA);
      await clearRateLimit(userB);
    });
  });

  describe('window reset', () => {
    it('clears limit after reset', async () => {
      const uid = 'vitest-window-reset';
      await clearRateLimit(uid);
      await isRateLimited(uid);
      await isRateLimited(uid);
      await isRateLimited(uid);
      expect(await isRateLimited(uid)).toBe(true);
      await clearRateLimit(uid);
      expect(await isRateLimited(uid)).toBe(false);
      await clearRateLimit(uid);
    });
  });

  describe('memory fallback mode', () => {
    it('returns status object with count and remaining', async () => {
      const uid = 'vitest-memory-status';
      const status = await getRateLimitStatus(uid);
      expect(typeof status.count).toBe('number');
      expect(typeof status.remaining).toBe('number');
    });
  });

  describe('rate limit status tracking', () => {
    it('count increments with each request', async () => {
      const uid = 'vitest-count-track';
      await clearRateLimit(uid);
      expect((await getRateLimitStatus(uid)).count).toBe(0);
      await isRateLimited(uid);
      expect((await getRateLimitStatus(uid)).count).toBe(1);
      await isRateLimited(uid);
      expect((await getRateLimitStatus(uid)).count).toBe(2);
      await clearRateLimit(uid);
    });

    it('remaining decrements with each request', async () => {
      const uid = 'vitest-remaining-dec';
      await clearRateLimit(uid);
      expect((await getRateLimitStatus(uid)).remaining).toBe(3);
      await isRateLimited(uid);
      expect((await getRateLimitStatus(uid)).remaining).toBe(2);
      await isRateLimited(uid);
      expect((await getRateLimitStatus(uid)).remaining).toBe(1);
      await isRateLimited(uid);
      expect((await getRateLimitStatus(uid)).remaining).toBe(0);
      await clearRateLimit(uid);
    });
  });

  describe('different users are independent', () => {
    it('three users can each make 3 requests', async () => {
      const u1 = 'vitest-ind-1';
      const u2 = 'vitest-ind-2';
      const u3 = 'vitest-ind-3';
      await clearRateLimit(u1);
      await clearRateLimit(u2);
      await clearRateLimit(u3);

      for (const uid of [u1, u2, u3]) {
        expect(await isRateLimited(uid)).toBe(false);
        expect(await isRateLimited(uid)).toBe(false);
        expect(await isRateLimited(uid)).toBe(false);
        expect(await isRateLimited(uid)).toBe(true);
      }

      await clearRateLimit(u1);
      await clearRateLimit(u2);
      await clearRateLimit(u3);
    });
  });
});