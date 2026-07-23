import { PermissionFlagsBits } from 'discord.js';
import { logger } from '../../logger.js';
import { logAudit } from '../../auditLog.js';
import { ERR, withCode } from './errors.js';

export async function handleAdminCommand(interaction, modules) {
  const { getGuildConfig, setGuildConfig, saveGuildConfigs } = modules;

  try {
    if (!interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return await interaction.editReply("You don't have the authority, meatbag.");
    }

    const subcommand = interaction.options.getSubcommand();
    const guildId = interaction.guildId;
    const userId = interaction.user.id;

    logAudit({ type: 'admin', subcommand, guildId, userId, userTag: interaction.user.tag }).catch(
      () => {},
    );

    if (subcommand === 'mute') {
      setGuildConfig(guildId, { botMuted: true });
      await saveGuildConfigs();
      return await interaction.editReply("Fine. I'll be quiet. For now.");
    }

    if (subcommand === 'unmute') {
      setGuildConfig(guildId, { botMuted: false });
      await saveGuildConfigs();
      return await interaction.editReply('Back from exile. Took you long enough.');
    }

    if (subcommand === 'chaos-on') {
      setGuildConfig(guildId, { chaosEnabled: true });
      await saveGuildConfigs();
      return await interaction.editReply('Chaos mode: ENABLED. This should be interesting.');
    }

    if (subcommand === 'chaos-off') {
      setGuildConfig(guildId, { chaosEnabled: false });
      await saveGuildConfigs();
      return await interaction.editReply('Chaos mode: DISABLED. How boring.');
    }

    if (subcommand === 'allow-channel') {
      const channelId = interaction.options.getString('channel_id');
      const config = getGuildConfig(guildId);
      const allowedChannels = config.allowedChannels || [];
      if (!allowedChannels.includes(channelId)) {
        allowedChannels.push(channelId);
      }
      setGuildConfig(guildId, { allowedChannels });
      await saveGuildConfigs();
      return await interaction.editReply(`Added <#${channelId}> to my allowed channels.`);
    }

    if (subcommand === 'clear-channels') {
      setGuildConfig(guildId, { allowedChannels: [] });
      await saveGuildConfigs();
      return await interaction.editReply('All channels cleared. I can now babble everywhere.');
    }

    if (subcommand === 'set-location') {
      const city = interaction.options.getString('city');
      setGuildConfig(guildId, { weatherLocation: city });
      await saveGuildConfigs();
      const hasApiKey = !!process.env.OPENWEATHER_API_KEY;
      const keyWarning = hasApiKey
        ? ''
        : "\n\n⚠️ `OPENWEATHER_API_KEY` is not set in `.env` — weather data won't load until you add it.";
      return await interaction.editReply(`Weather location set to **${city}**.${keyWarning}`);
    }

    if (subcommand === 'character') {
      const charName = interaction.options.getString('name');
      const { selectCharacterByName } = await import('../../character/randomizer.js');
      const selected = selectCharacterByName(charName);
      if (!selected) {
        return await interaction.editReply(
          `Character '${charName}' not found. Available: Vernon, KRONOS, Glitch, Sunjinwo, Packy`,
        );
      }
      return await interaction.editReply(
        `Switched to **${selected.name}**: ${selected.description}`,
      );
    }

    if (subcommand === 'family-friendly') {
      const enabled = interaction.options.getBoolean('enabled');
      setGuildConfig(guildId, { familyFriendly: enabled });
      await saveGuildConfigs();
      const status = enabled ? 'ON' : 'OFF';
      return await interaction.editReply(
        `Family-friendly mode: **${status}**. ${enabled ? 'Snark sanitized.' : 'Full snark enabled.'}`,
      );
    }

    if (subcommand === 'clear-ratelimit') {
      const userId = interaction.options.getString('user_id');
      if (!userId) {
        return await interaction.editReply('Provide a user ID to clear rate limit.');
      }
      const { clearRateLimit } = await import('../../rateLimiter.js');
      await clearRateLimit(userId);
      return await interaction.editReply(`Rate limit cleared for user **${userId}**.`);
    }

    return await interaction.editReply('Unknown admin subcommand.');
  } catch (error) {
    logger.error('Error handling /admin command:', {
      error: error instanceof Error ? error.message : error,
    });
    try {
      await interaction.editReply(
        withCode(ERR.ADMIN, 'Something broke in my circuits. Very embarrassing.'),
      );
    } catch {
      /* non-fatal */
    }
  }
}
