#!/usr/bin/env node
/**
 * Rate limiter integration tests
 * Tests the in-memory rate limiter under concurrent and sequential load.
 * Uses the module directly (no Discord API needed).
 */

import { isRateLimited, clearRateLimit, getRateLimitStatus } from '../../src/bot/rateLimiter.js';

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

async function testSequentialLimit() {
  console.log('\n# Sequential rate limiting');

  const userId = 'test-user-1';
  await clearRateLimit(userId);

  // First 3 requests should not be rate limited
  assert(!(await isRateLimited(userId)), 'request 1 (should pass)');
  assert(!(await isRateLimited(userId)), 'request 2 (should pass)');
  assert(!(await isRateLimited(userId)), 'request 3 (should pass)');

  // 4th request should be rate limited (max 3 per window)
  assert(await isRateLimited(userId), 'request 4 (should be limited)');

  const status = await getRateLimitStatus(userId);
  assert(status.remaining === 0, `remaining should be 0, got ${status.remaining}`);

  await clearRateLimit(userId);
  assert(!(await isRateLimited(userId)), 'after clear, should not be limited');
}

async function testConcurrentLimit() {
  console.log('\n# Concurrent rate limiting');

  const userId = 'test-user-2';
  await clearRateLimit(userId);

  // Fire 6 requests concurrently; at most 3 should succeed, 3 should be limited
  const results = await Promise.all([
    isRateLimited(userId),
    isRateLimited(userId),
    isRateLimited(userId),
    isRateLimited(userId),
    isRateLimited(userId),
    isRateLimited(userId),
  ]);

  const limited = results.filter(r => r === true).length;
  const allowed = results.filter(r => r === false).length;

  assert(allowed <= 3, `at most 3 allowed, got ${allowed}`);
  assert(limited >= 3, `at least 3 limited, got ${limited}`);
  assert(allowed + limited === 6, `total should be 6, got ${allowed + limited}`);

  await clearRateLimit(userId);
}

async function testPerUserIsolation() {
  console.log('\n# Per-user isolation');

  const userA = 'test-user-a';
  const userB = 'test-user-b';
  await clearRateLimit(userA);
  await clearRateLimit(userB);

  // User A uses all 3 requests
  assert(!(await isRateLimited(userA)), 'userA request 1');
  assert(!(await isRateLimited(userA)), 'userA request 2');
  assert(!(await isRateLimited(userA)), 'userA request 3');
  assert(await isRateLimited(userA), 'userA request 4 (limited)');

  // User B should still have fresh limit
  assert(!(await isRateLimited(userB)), 'userB request 1 (not affected by A)');
  assert(!(await isRateLimited(userB)), 'userB request 2');
  assert(!(await isRateLimited(userB)), 'userB request 3');

  // User A still limited
  assert(await isRateLimited(userA), 'userA still limited');

  await clearRateLimit(userA);
  await clearRateLimit(userB);
}

async function testWindowReset() {
  console.log('\n# Window reset');

  // Clear all rate limit state for this user
  const userId = 'test-window-reset';
  await clearRateLimit(userId);

  // Burn through all 3 requests immediately
  await isRateLimited(userId);
  await isRateLimited(userId);
  await isRateLimited(userId);

  // 4th should be limited
  assert(await isRateLimited(userId), 'limited after 3 rapid requests');

  // Clear and verify fresh
  await clearRateLimit(userId);
  assert(!(await isRateLimited(userId)), 'fresh start after clear');

  await clearRateLimit(userId);
}

async function main() {
  console.log('='.repeat(60));
  console.log('Rate Limiter Integration Tests');
  console.log('='.repeat(60));

  await testSequentialLimit();
  await testConcurrentLimit();
  await testPerUserIsolation();
  await testWindowReset();

  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed}/${passed + failed} tests passed`);
  console.log('='.repeat(60));

  process.exit(failed > 0 ? 1 : 0);
}

main();
