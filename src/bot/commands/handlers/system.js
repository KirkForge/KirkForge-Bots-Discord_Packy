import { EmbedBuilder } from 'discord.js';
import { getCurrentCharacter } from '../../character/randomizer.js';
import { logger } from '../../logger.js';
import { ERR, withCode } from './errors.js';
import { COLORS } from './_shared.js';

export async function handleStatusCommand(interaction, modules) {
  const { lorebook } = modules;

  try {
    const BOT_MODE = process.env.BOT_MODE || 'microservice';
    const PRIMARY_ADAPTER = process.env.PRIMARY_ADAPTER || 'claude';
    const COGNITION_PORT = process.env.COGNITION_PORT || '8765';

    const uptimeSec = Math.floor(process.uptime());
    const hours = Math.floor(uptimeSec / 3600);
    const mins  = Math.floor((uptimeSec % 3600) / 60);
    const secs  = uptimeSec % 60;
    const uptimeStr = `${hours}h ${mins}m ${secs}s`;

    const guildCount = interaction.client.guilds.cache.size;

    let loreCount = 0;
    if (lorebook && lorebook.categories) {
      for (const entries of Object.values(lorebook.categories)) {
        if (Array.isArray(entries)) loreCount += entries.length;
      }
    }
    const categoryCount = lorebook?.categories ? Object.keys(lorebook.categories).length : 0;

    const modeIcon = BOT_MODE === 'direct' ? '⚡ direct' : '🔗 microservice';
    const adapterIcon = PRIMARY_ADAPTER === 'claude' ? '🤖 Claude' : '🧠 MiniMax';

    const activeChar = getCurrentCharacter();
    const charName = activeChar?.name || 'Packy';
    const charDesc = activeChar?.description || '';

    const embed = new EmbedBuilder()
      .setTitle(`${charName} System Status`)
      .setColor(COLORS.STATUS)
      .addFields(
        { name: 'Character', value: charName, inline: true },
        { name: 'Mode',        value: modeIcon,                        inline: true },
        { name: 'Adapter',     value: adapterIcon,                     inline: true },
        { name: 'Uptime',      value: uptimeStr,                       inline: true },
        { name: 'Guilds',      value: String(guildCount),              inline: true },
        { name: 'Lorebook',    value: `${loreCount} entries / ${categoryCount} categories`, inline: true },
        { name: 'Port',        value: BOT_MODE === 'microservice' ? COGNITION_PORT : 'N/A', inline: true },
      )
      .setDescription(charDesc ? `*${charDesc}*` : null)
      .setFooter({ text: `${charName} v2.0.0 — still operational, unfortunately` })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /status command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.UNKNOWN, 'Status check failed. Very on-brand.'));
    } catch { /* non-fatal */ }
  }
}

export async function handleChaosCommand(interaction, modules) {
  const { channelChaos } = modules;

  try {
    const guildCfg = modules.getGuildConfig ? modules.getGuildConfig(interaction.guildId) : {};
    const chaosEnabled = guildCfg.chaosEnabled !== false;
    const unprovokedEnabled = guildCfg.unprovokedEnabled !== false;

    const chaosState = channelChaos ? channelChaos.get(interaction.channelId) : null;
    const now = Date.now();

    let cooldownStr = 'Ready to fire';
    if (chaosState && chaosState.last_injection_ts) {
      const cooldownMs = 180000;
      const remaining = cooldownMs - (now - chaosState.last_injection_ts);
      if (remaining > 0) {
        const remSec = Math.ceil(remaining / 1000);
        cooldownStr = `Cooling down (${remSec}s)`;
      }
    }

    let targetStr = 'None';
    if (chaosState && chaosState.target_user_id && chaosState.target_lock_expiry) {
      if (now < chaosState.target_lock_expiry) {
        const expSec = Math.ceil((chaosState.target_lock_expiry - now) / 1000 / 60);
        targetStr = `<@${chaosState.target_user_id}> (${expSec}m left)`;
      }
    }

    const scoreStr = chaosState
      ? `${(chaosState.chaos_score || 0).toFixed(2)} / 1.0`
      : '0.00 / 1.0';

    const statusStr = chaosEnabled
      ? (unprovokedEnabled ? '✅ Fully active' : '⚠️ Chaos on, unprovoked off')
      : '❌ Disabled';

    const embed = new EmbedBuilder()
      .setTitle('Chaos State')
      .setColor(COLORS.CHAOS)
      .addFields(
        { name: 'Status',      value: statusStr,   inline: true  },
        { name: 'Score',       value: scoreStr,    inline: true  },
        { name: 'Cooldown',    value: cooldownStr, inline: true  },
        { name: 'Target Lock', value: targetStr,   inline: false },
      )
      .setFooter({ text: `Channel: ${interaction.channelId}` })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /chaos command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.CHAOS, 'Chaos state unreadable. Ironic.'));
    } catch { /* non-fatal */ }
  }
}
