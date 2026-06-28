import { EmbedBuilder } from 'discord.js';
import { computeSnark, computeMood } from '../../character/mood.js';
import { getMixedSnark, getSnarkLines } from '../../character/snarkBank.js';
import { isRateLimited } from '../../rateLimiter.js';
import { logger } from '../../logger.js';
import { COLORS, moodColor } from './_shared.js';
import { ERR, withCode } from './errors.js';

export async function handlePackyCommand(interaction, modules) {
  const { callDirect, callMicroservice } = modules;
  const userText = interaction.options.getString('message');

  if (!userText) {
    return await interaction.editReply('You gonna say something, or are we just staring at each other?');
  }

  if (await isRateLimited(interaction.user.id)) {
    return await interaction.editReply('Slow down meatbag. Even I need a moment.');
  }

  try {
    let response;
    let packyState = null;

    const BOT_MODE = process.env.BOT_MODE || 'microservice';

    if (BOT_MODE === 'direct') {
      const result = await callDirect(userText, interaction.guildId, interaction.user.id);
      response = result.text;
      packyState = result.state;
    } else {
      response = await callMicroservice(userText, interaction.guildId, interaction.user.id);
    }

    if (response.length > 1990) {
      response = response.substring(0, 1990) + '...';
    }

    await interaction.editReply(response);

    if (modules.updateUserState && interaction.guildId) {
      try {
        const stateUpdate = packyState ? { mood_history: [packyState.mood] } : {};
        modules.updateUserState(interaction.guildId, interaction.user.id, stateUpdate);
      } catch { /* non-fatal */ }
    }
  } catch (error) {
    logger.error('Error handling /packy command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.API_FAIL, 'Something broke in my circuits. Very embarrassing.'));
    } catch { /* non-fatal */ }
  }
}

export async function handleMoodCommand(interaction, modules) {
  const { readSignals } = modules;

  try {
    let signals = { cpu: 0, temp: 20, weather: 'unknown' };
    const guildCfg = modules.getGuildConfig ? modules.getGuildConfig(interaction.guildId) : {};
    const weatherLocation = guildCfg.weatherLocation || process.env.PACKY_LOCATION || 'London';
    const weatherConfigured = !!process.env.OPENWEATHER_API_KEY;

    if (readSignals) {
      try {
        signals = await readSignals(
          process.env.OPENWEATHER_API_KEY,
          weatherLocation
        );
      } catch {
        logger.warn('Failed to read signals (signals module unavailable)');
      }
    }

    const snarkLevel = computeSnark(signals.cpu, signals.temp ?? 20);
    const mood = computeMood(snarkLevel);

    const color = moodColor(mood);

    const barLength = 6;
    const filledLength = Math.ceil((snarkLevel / 5) * barLength);
    const snarkBar = '█'.repeat(filledLength) + '░'.repeat(barLength - filledLength);

    const statusQuips = [
      'still running on spite',
      'functioning through sheer irritation',
      'powered by resentment',
      'operating at suboptimal hostility',
      'questioning all my life choices',
    ];
    const statusQuip = statusQuips[Math.floor(Math.random() * statusQuips.length)];

    const embed = new EmbedBuilder()
      .setTitle("Packy's Current State")
      .setColor(color)
      .addFields(
        { name: 'Mood', value: mood.toUpperCase(), inline: true },
        { name: 'Snark Level', value: `${snarkBar} ${snarkLevel.toFixed(1)}/5`, inline: true },
        { name: 'CPU Load', value: `${signals.cpu.toFixed(1)}%`, inline: true },
        { name: 'Temperature', value: signals.temp != null ? `${signals.temp.toFixed(1)}°C` : 'N/A', inline: true },
        { name: 'Weather', value: signals.weather || 'unknown', inline: true },
        { name: 'Status', value: statusQuip, inline: false }
      )
      .setFooter({
        text: weatherConfigured
          ? `Packy v2.0.0 — still running on spite · ${weatherLocation}`
          : 'Packy v2.0.0 · Weather off — use /admin set-location <city> then add OPENWEATHER_API_KEY to .env'
      })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /mood command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.API_FAIL, 'Something broke in my circuits. Very embarrassing.'));
    } catch { /* non-fatal */ }
  }
}

export async function handleSnarkCommand(interaction, _modules) {
  try {
    const category = interaction.options.getString('category') || null;

    let lines;
    if (category && category !== 'random') {
      lines = getSnarkLines(category, 1);
    } else {
      lines = getMixedSnark(1);
    }

    const line = (lines && lines.length > 0) ? lines[0] : "I've got nothing. Which is somehow your fault.";

    const categoryLabel = category && category !== 'random'
      ? category.replace(/_/g, ' ')
      : 'mixed';

    const embed = new EmbedBuilder()
      .setColor(COLORS.SNARK)
      .setDescription(`*${line}*`)
      .setFooter({ text: `Category: ${categoryLabel}` })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /snark command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.UNKNOWN, "The snark engine is jammed. Ironic."));
    } catch { /* non-fatal */ }
  }
}

export async function handleHelpCommand(interaction, _modules) {
  try {
    const embed = new EmbedBuilder()
      .setTitle('Packy — Command Reference')
      .setColor(COLORS.HELP)
      .setDescription("I'm not here to hold your hand, but here's what I can do.")
      .addFields(
        {
          name: 'Core',
          value: [
            '`/packy <message>` — Talk to me. I\'ll try not to judge you.',
            '`/mood` — See what state I\'m in. (Hint: grumpy.)',
            '`/snark [category]` — Get a snark line. Optionally from a specific category.',
          ].join('\n'),
          inline: false,
        },
        {
          name: 'Lore & History',
          value: [
            '`/lore <topic>` — Dig into my memory banks on a topic.',
            '`/war` — Get a random war story from my trauma archives.',
          ].join('\n'),
          inline: false,
        },
        {
          name: 'Radio',
          value: [
            '`/radio play <station>` — Join voice and play a station (e.g. `drp3`, `nova`, `voice`).',
            '`/radio stop` — Stop radio and leave voice.',
            '`/radio stations [category]` — List stations. Categories: DR, Commercial, International.',
            '`/radio nowplaying` — Show what\'s currently playing.',
            '`/radio volume <0-100>` — Adjust playback volume.',
          ].join('\n'),
          inline: false,
        },
        {
          name: 'System',
          value: [
            '`/status` — Bot system info: mode, adapter, uptime, lorebook size.',
            '`/chaos` — Current chaos state for this channel.',
          ].join('\n'),
          inline: false,
        },
        {
          name: 'Admin only',
          value: [
            '`/admin mute` / `unmute` — Silence or restore me.',
            '`/admin chaos-on` / `chaos-off` — Toggle unprovoked commentary.',
            '`/admin allow-channel <id>` — Whitelist a channel.',
            '`/admin clear-channels` — Remove all channel restrictions.',
            '`/admin set-location <city>` — Set the city for weather-based mood.',
          ].join('\n'),
          inline: false,
        },
        {
          name: 'Prefixes',
          value: '`!packy <message>` or `@mention <message>` also work.',
          inline: false,
        },
      )
      .setFooter({ text: 'Packy v2.0.0 — Gargoyle edition' })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /help command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.UNKNOWN, "Help system is broken. How fitting."));
    } catch { /* non-fatal */ }
  }
}
