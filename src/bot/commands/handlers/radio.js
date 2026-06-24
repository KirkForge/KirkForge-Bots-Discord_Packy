import { EmbedBuilder, PermissionFlagsBits } from 'discord.js';
import { playRadio, stopRadio, getCurrentRadio, setVolume } from '../../radio/radioPlayer.js';
import { RADIO_STATIONS, getStationsByCategory, getCategories } from '../../radio/radioStations.js';
import { COLORS } from './_shared.js';

export async function handleRadioPlay(interaction) {
  try {
    const stationId = interaction.options.getString('station');
    const member = interaction.member;
    const voiceChannel = member?.voice?.channel;

    if (!voiceChannel) {
      return await interaction.editReply('You need to be in a voice channel, meatbag. I\'m not haunting empty airwaves.');
    }

    const permissions = voiceChannel.permissionsFor(interaction.client.user);
    if (!permissions?.has(PermissionFlagsBits.Connect) || !permissions?.has(PermissionFlagsBits.Speak)) {
      return await interaction.editReply('I don\'t have permission to join or speak in that channel. Fix your permissions.');
    }

    const result = await playRadio(voiceChannel, stationId);
    return await interaction.editReply(result.message);
  } catch (error) {
    console.error('Error handling /radio play:', error);
    return await interaction.editReply('The radio blew a fuse. Try again.');
  }
}

export async function handleRadioStop(interaction) {
  try {
    const result = stopRadio(interaction.guildId);
    return await interaction.editReply(result.message);
  } catch (error) {
    console.error('Error handling /radio stop:', error);
    return await interaction.editReply('Couldn\'t stop the radio. It\'s possessed.');
  }
}

export async function handleRadioStations(interaction) {
  try {
    const category = interaction.options.getString('category');
    const stations = category ? getStationsByCategory(category) : RADIO_STATIONS;

    if (stations.length === 0) {
      return await interaction.editReply('No stations found in that category. Even the airwaves are empty.');
    }

    const categories = getCategories();
    let description = stations
      .map((s) => `\`${s.id}\` — **${s.name}**\n${s.description}`)
      .join('\n\n');

    if (description.length > 4000) {
      description = description.substring(0, 3997) + '...';
    }

    const embed = new EmbedBuilder()
      .setTitle(category ? `📻 ${category} Stations` : '📻 Radio Stations')
      .setColor(COLORS.STATUS)
      .setDescription(description)
      .setFooter({ text: `Use /radio play station:<id> | Categories: ${categories.join(', ')}` })
      .setTimestamp();

    return await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    console.error('Error handling /radio stations:', error);
    return await interaction.editReply('Station list is broken. Probably Windows Media Player\'s fault.');
  }
}

export async function handleRadioNowPlaying(interaction) {
  try {
    const current = getCurrentRadio(interaction.guildId);
    if (!current || !current.station) {
      return await interaction.editReply('Nothing playing right now. The airwaves are as dead as my battery.');
    }

    const embed = new EmbedBuilder()
      .setTitle('📻 Now Playing')
      .setColor(COLORS.STATUS)
      .setDescription(
        `**${current.station.name}**\n${current.station.description}\n\n` +
        `Category: ${current.station.category} | Country: ${current.station.country.toUpperCase()}`
      )
      .setFooter({ text: `Station ID: ${current.station.id}` })
      .setTimestamp();

    return await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    console.error('Error handling /radio nowplaying:', error);
    return await interaction.editReply('Can\'t figure out what\'s playing. My tuner is broken.');
  }
}

export async function handleRadioVolume(interaction) {
  try {
    const level = interaction.options.getInteger('level');
    const normalized = level / 100;
    const ok = setVolume(interaction.guildId, normalized);

    if (!ok) {
      return await interaction.editReply('Can\'t adjust volume — radio might not be running. Start it with /radio play first.');
    }

    return await interaction.editReply(`Volume set to **${level}%**. Don't blast my speakers, meatbag.`);
  } catch (error) {
    console.error('Error handling /radio volume:', error);
    return await interaction.editReply('Volume knob is stuck. Probably rust.');
  }
}
