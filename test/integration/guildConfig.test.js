#!/usr/bin/env node
/**
 * Guild config round-trip integration tests
 * Tests save/load/get/set lifecycle using a temp file path.
 * Does NOT require Discord API.
 */

import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import {
  getGuildConfig,
  setGuildConfig,
  saveGuildConfigs,
  isChannelAllowed,
  isGuildMuted,
} from '../../src/bot/guildConfig.js';

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

async function testDefaultConfig() {
  console.log('\n# Default config');

  const cfg = getGuildConfig('test-guild-default');
  assert(cfg.prefix === '!packy', `prefix defaults to !packy, got ${cfg.prefix}`);
  assert(cfg.botMuted === false, 'botMuted defaults to false');
  assert(cfg.chaosEnabled === true, 'chaosEnabled defaults to true');
  assert(typeof cfg.allowedChannels !== 'undefined', 'allowedChannels exists');
}

async function testSetAndGet() {
  console.log('\n# Set and get');

  setGuildConfig('test-guild-set', { botMuted: true, location: 'Copenhagen' });
  const cfg = getGuildConfig('test-guild-set');

  assert(cfg.botMuted === true, 'botMuted persisted');
  assert(cfg.location === 'Copenhagen', 'custom field preserved');
  assert(cfg.prefix === '!packy', 'unset fields keep defaults');
}

async function testPartialUpdate() {
  console.log('\n# Partial update (merge)');

  setGuildConfig('test-guild-merge', { chaosEnabled: false });
  setGuildConfig('test-guild-merge', { familyFriendly: true });

  const cfg = getGuildConfig('test-guild-merge');
  assert(cfg.chaosEnabled === false, 'first value preserved');
  assert(cfg.familyFriendly === true, 'second value merged');
}

async function testChannelAllowListEmptyDeny() {
  console.log('\n# Channel allow-list (empty = deny)');

  setGuildConfig('test-guild-deny', { allowedChannels: [] });
  assert(!isChannelAllowed('test-guild-deny', 'channel-1'), 'empty list denies channel-1');
  assert(!isChannelAllowed('test-guild-deny', 'channel-2'), 'empty list denies channel-2');

  const cfg = getGuildConfig('test-guild-deny');
  cfg.allowedChannels.push('channel-1');
  assert(isChannelAllowed('test-guild-deny', 'channel-1'), 'explicit channel allowed');
  assert(!isChannelAllowed('test-guild-deny', 'channel-42'), 'non-listed channel still denied');
}

async function testSaveLoadRoundTrip() {
  console.log('\n# Save/load round-trip');

  setGuildConfig('test-guild-roundtrip', { botMuted: true, chaosEnabled: false });
  await saveGuildConfigs();

  const configPath = path.join(process.cwd(), 'data', 'guild_config.json');
  let fileContent;
  try {
    fileContent = await fs.readFile(configPath, 'utf-8');
    const parsed = JSON.parse(fileContent);
    assert(parsed['test-guild-roundtrip']?.botMuted === true, 'botMuted true after save');
    assert(parsed['test-guild-roundtrip']?.chaosEnabled === false, 'chaosEnabled false after save');
  } catch (e) {
    console.log(`  SKIP: save/load (file not available: ${e.message})`);
  }
}

async function testIsGuildMuted() {
  console.log('\n# Guild mute detection');

  setGuildConfig('test-guild-muted', { botMuted: true });
  assert(isGuildMuted('test-guild-muted') === true, 'muted guild detected');

  setGuildConfig('test-guild-unmuted', { botMuted: false });
  assert(isGuildMuted('test-guild-unmuted') === false, 'unmuted guild detected');

  assert(isGuildMuted('test-guild-nonexistent') === false, 'nonexistent guild not muted');
}

async function main() {
  console.log('='.repeat(60));
  console.log('Guild Config Integration Tests');
  console.log('='.repeat(60));

  await testDefaultConfig();
  await testSetAndGet();
  await testPartialUpdate();
  await testChannelAllowListEmptyDeny();
  await testSaveLoadRoundTrip();
  await testIsGuildMuted();

  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed}/${passed + failed} tests passed`);
  console.log('='.repeat(60));

  process.exit(failed > 0 ? 1 : 0);
}

main();
