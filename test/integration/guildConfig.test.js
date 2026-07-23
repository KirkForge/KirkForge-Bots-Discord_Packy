import { describe, it, expect, beforeEach } from 'vitest';
import {
  getGuildConfig,
  setGuildConfig,
  saveGuildConfigs,
  isChannelAllowed,
  isGuildMuted,
} from '../../src/bot/guildConfig.js';

describe('Guild config', () => {
  describe('default config', () => {
    it('returns default prefix', () => {
      const cfg = getGuildConfig('vitest-default-guild');
      expect(cfg.prefix).toBe('!packy');
    });

    it('botMuted defaults to false', () => {
      expect(getGuildConfig('vitest-default-guild').botMuted).toBe(false);
    });

    it('chaosEnabled defaults to true', () => {
      expect(getGuildConfig('vitest-default-guild').chaosEnabled).toBe(true);
    });

    it('allowedChannels exists', () => {
      const cfg = getGuildConfig('vitest-default-guild');
      expect(typeof cfg.allowedChannels).not.toBe('undefined');
    });
  });

  describe('set and get', () => {
    it('persists config with custom fields', () => {
      setGuildConfig('vitest-set-guild', { botMuted: true, location: 'Copenhagen' });
      const cfg = getGuildConfig('vitest-set-guild');
      expect(cfg.botMuted).toBe(true);
      expect(cfg.location).toBe('Copenhagen');
      expect(cfg.prefix).toBe('!packy');
    });
  });

  describe('partial update (merge)', () => {
    it('preserves first value and merges second', () => {
      setGuildConfig('vitest-merge-guild', { chaosEnabled: false });
      setGuildConfig('vitest-merge-guild', { familyFriendly: true });
      const cfg = getGuildConfig('vitest-merge-guild');
      expect(cfg.chaosEnabled).toBe(false);
      expect(cfg.familyFriendly).toBe(true);
    });
  });

  describe('channel allow-list', () => {
    it('empty list denies all channels', () => {
      setGuildConfig('vitest-deny-guild', { allowedChannels: [] });
      expect(isChannelAllowed('vitest-deny-guild', 'channel-1')).toBe(false);
      expect(isChannelAllowed('vitest-deny-guild', 'channel-2')).toBe(false);
    });

    it('explicit channel allowed, others denied', () => {
      setGuildConfig('vitest-allow-guild', { allowedChannels: ['channel-1'] });
      expect(isChannelAllowed('vitest-allow-guild', 'channel-1')).toBe(true);
      expect(isChannelAllowed('vitest-allow-guild', 'channel-42')).toBe(false);
    });
  });

  describe('save/load round-trip', () => {
    it('persists config after save', async () => {
      setGuildConfig('vitest-rt-guild', { botMuted: true, chaosEnabled: false });
      await saveGuildConfigs();
      const cfg = getGuildConfig('vitest-rt-guild');
      expect(cfg.botMuted).toBe(true);
      expect(cfg.chaosEnabled).toBe(false);
    });
  });

  describe('guild mute detection', () => {
    it('detects muted guild', () => {
      setGuildConfig('vitest-muted', { botMuted: true });
      expect(isGuildMuted('vitest-muted')).toBe(true);
    });

    it('detects unmuted guild', () => {
      setGuildConfig('vitest-unmuted', { botMuted: false });
      expect(isGuildMuted('vitest-unmuted')).toBe(false);
    });

    it('nonexistent guild is not muted', () => {
      expect(isGuildMuted('vitest-nonexistent')).toBe(false);
    });
  });
});