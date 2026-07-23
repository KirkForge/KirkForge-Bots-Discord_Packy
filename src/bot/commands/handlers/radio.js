// @ts-nocheck — TODO: add types
import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  PermissionFlagsBits,
} from 'discord.js';
import { playRadio, stopRadio, getCurrentRadio, setVolume } from '../../radio/radioPlayer.js';
import { RADIO_STATIONS, getStationsByCategory, getCategories } from '../../radio/radioStations.js';
import { logger } from '../../logger.js';
import { ERR, withCode } from './errors.js';
import { COLORS } from './_shared.js';

const STATIONS_PER_PAGE = 5;

function buildStationsEmbed(stations, page, totalPages, category) {
  const start = page * STATIONS_PER_PAGE;
  const pageStations = stations.slice(start, start + STATIONS_PER_PAGE);
  const categories = getCategories();

  const description = pageStations
    .map((s) => `\`${s.id}\` — **${s.name}**\n${s.description}`)
    .join('\n\n');

  return new EmbedBuilder()
    .setTitle(category ? `📻 ${category} Stations` : '📻 Radio Stations')
    .setColor(COLORS.STATUS)
    .setDescription(description)
    .setFooter({
      text: `Page ${page + 1}/${totalPages} · Use /radio play station:<id> | Categories: ${categories.join(', ')}`,
    })
    .setTimestamp();
}

function buildPaginationRow(page, totalPages) {
  const row = new ActionRowBuilder();
  if (page > 0) {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(`radio_stn_page:${page - 1}`)
        .setLabel('◀ Prev')
        .setStyle(ButtonStyle.Secondary),
    );
  }
  if (page < totalPages - 1) {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(`radio_stn_page:${page + 1}`)
        .setLabel('Next ▶')
        .setStyle(ButtonStyle.Secondary),
    );
  }
  return row.components.length > 0 ? [row] : [];
}

export async function handleRadioStations(interaction) {
  try {
    const category = interaction.options.getString('category');
    const stations = category ? getStationsByCategory(category) : RADIO_STATIONS;

    if (stations.length === 0) {
      return await interaction.editReply(
        'No stations found in that category. Even the airwaves are empty.',
      );
    }

    const totalPages = Math.ceil(stations.length / STATIONS_PER_PAGE);
    const embed = buildStationsEmbed(stations, 0, totalPages, category);
    const components = buildPaginationRow(0, totalPages);

    return await interaction.editReply({ embeds: [embed], components });
  } catch (error) {
    logger.error('Error handling /radio stations:', {
      error: error instanceof Error ? error.message : error,
    });
    return await interaction.editReply(
      withCode(ERR.RADIO, "Station list is broken. Probably Windows Media Player's fault."),
    );
  }
}

export async function handleRadioStationsButton(interaction, stations, category) {
  try {
    await interaction.deferUpdate();

    const pageStr = interaction.customId.split(':')[1];
    const page = parseInt(pageStr, 10);
    const totalPages = Math.ceil(stations.length / STATIONS_PER_PAGE);

    if (isNaN(page) || page < 0 || page >= totalPages) {
      return;
    }

    const embed = buildStationsEmbed(stations, page, totalPages, category);
    const components = buildPaginationRow(page, totalPages);

    await interaction.editReply({ embeds: [embed], components });
  } catch (error) {
    logger.error('Error handling stations button:', {
      error: error instanceof Error ? error.message : error,
    });
  }
}

export async function handleRadioPlay(interaction) {
  try {
    const stationId = interaction.options.getString('station');
    const member = interaction.member;
    const voiceChannel = member?.voice?.channel;

    if (!voiceChannel) {
      return await interaction.editReply(
        "You need to be in a voice channel, meatbag. I'm not haunting empty airwaves.",
      );
    }

    const permissions = voiceChannel.permissionsFor(interaction.client.user);
    if (
      !permissions?.has(PermissionFlagsBits.Connect) ||
      !permissions?.has(PermissionFlagsBits.Speak)
    ) {
      return await interaction.editReply(
        "I don't have permission to join or speak in that channel. Fix your permissions.",
      );
    }

    const result = await playRadio(voiceChannel, stationId);
    return await interaction.editReply(result.message);
  } catch (error) {
    logger.error('Error handling /radio play:', {
      error: error instanceof Error ? error.message : error,
    });
    return await interaction.editReply(withCode(ERR.RADIO, 'The radio blew a fuse. Try again.'));
  }
}

export async function handleRadioStop(interaction) {
  try {
    const result = stopRadio(interaction.guildId);
    return await interaction.editReply(result.message);
  } catch (error) {
    logger.error('Error handling /radio stop:', {
      error: error instanceof Error ? error.message : error,
    });
    return await interaction.editReply(
      withCode(ERR.RADIO, "Couldn't stop the radio. It's possessed."),
    );
  }
}

export async function handleRadioNowPlaying(interaction) {
  try {
    const current = getCurrentRadio(interaction.guildId);
    if (!current || !current.station) {
      return await interaction.editReply(
        'Nothing playing right now. The airwaves are as dead as my battery.',
      );
    }

    const embed = new EmbedBuilder()
      .setTitle('📻 Now Playing')
      .setColor(COLORS.STATUS)
      .setDescription(
        `**${current.station.name}**\n${current.station.description}\n\n` +
          `Category: ${current.station.category} | Country: ${current.station.country.toUpperCase()}`,
      )
      .setFooter({ text: `Station ID: ${current.station.id}` })
      .setTimestamp();

    return await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /radio nowplaying:', {
      error: error instanceof Error ? error.message : error,
    });
    return await interaction.editReply(
      withCode(ERR.RADIO, "Can't figure out what's playing. My tuner is broken."),
    );
  }
}

export async function handleRadioVolume(interaction) {
  try {
    const level = interaction.options.getInteger('level');
    const normalized = level / 100;
    const ok = setVolume(interaction.guildId, normalized);

    if (!ok) {
      return await interaction.editReply(
        "Can't adjust volume — radio might not be running. Start it with /radio play first.",
      );
    }

    return await interaction.editReply(
      `Volume set to **${level}%**. Don't blast my speakers, meatbag.`,
    );
  } catch (error) {
    logger.error('Error handling /radio volume:', {
      error: error instanceof Error ? error.message : error,
    });
    return await interaction.editReply(withCode(ERR.RADIO, 'Volume knob is stuck. Probably rust.'));
  }
}
