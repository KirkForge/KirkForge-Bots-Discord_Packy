// radioPlayer.js — Discord voice connection and radio stream manager
// Handles joining channels, streaming MP3 radio, and graceful teardown

import {
  joinVoiceChannel,
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  VoiceConnectionStatus,
  getVoiceConnection,
  NoSubscriberBehavior,
} from "@discordjs/voice";

import { logger } from "../logger.js";
import { getStation } from "./radioStations.js";

// Guild ID → { connection, player, subscription, stationId, startedAt }
const guildPlayers = new Map();

function getOrCreatePlayer(guildId) {
  if (!guildPlayers.has(guildId)) {
    const player = createAudioPlayer({
      behaviors: {
        noSubscriber: NoSubscriberBehavior.Stop,
      },
    });

    player.on("error", (error) => {
      logger.error(
        `Radio player error in guild ${guildId}: ${error.message}`
      );
    });

    player.on(AudioPlayerStatus.Idle, () => {
      logger.info(`Radio player idle in guild ${guildId}`);
    });

    guildPlayers.set(guildId, {
      player,
      connection: null,
      subscription: null,
      stationId: null,
      startedAt: null,
    });
  }
  return guildPlayers.get(guildId);
}

/**
 * Join a voice channel and start playing a radio station
 * @param {VoiceChannel} voiceChannel — Discord voice channel to join
 * @param {string} stationId — Station ID from radioStations.js
 * @returns {{ok: boolean, message: string, stationName?: string}}
 */
export async function playRadio(voiceChannel, stationId) {
  const station = getStation(stationId);
  if (!station) {
    return { ok: false, message: `Unknown station: **${stationId}**. Use /radio stations to see what's available.` };
  }

  const guildId = voiceChannel.guild.id;
  const existing = getVoiceConnection(guildId);

  // If already in a channel in this guild, move / reuse
  if (existing) {
    existing.rejoin({
      channelId: voiceChannel.id,
      selfDeaf: false,
      selfMute: false,
    });
  }

  const state = getOrCreatePlayer(guildId);

  try {
    let connection = existing;
    if (!connection) {
      connection = joinVoiceChannel({
        channelId: voiceChannel.id,
        guildId,
        adapterCreator: voiceChannel.guild.voiceAdapterCreator,
        selfDeaf: false,
        selfMute: false,
      });

      connection.on(VoiceConnectionStatus.Disconnected, () => {
        logger.warn(`Voice disconnected in guild ${guildId}`);
        cleanup(guildId);
      });

      connection.on(VoiceConnectionStatus.Destroyed, () => {
        logger.info(`Voice connection destroyed in guild ${guildId}`);
        cleanup(guildId);
      });

      state.connection = connection;
    } else {
      state.connection = connection;
    }

    // Create audio resource from HTTP stream
    // Using createAudioResource with a direct URL; ffmpeg transcoding is handled by prism-media under the hood
    const resource = createAudioResource(station.url, {
      inlineVolume: true,
      metadata: { stationId: station.id },
    });

    if (resource.volume) {
      resource.volume.setVolume(0.8);
    }

    state.player.play(resource);
    state.stationId = station.id;
    state.startedAt = Date.now();

    if (!state.subscription) {
      state.subscription = connection.subscribe(state.player);
    }

    logger.info(`Started radio ${station.name} in guild ${guildId}`);
    return {
      ok: true,
      message: `📻 Now playing **${station.name}** — ${station.description}`,
      stationName: station.name,
    };
  } catch (err) {
    logger.error(`Failed to start radio in guild ${guildId}: ${err.message}`);
    cleanup(guildId);
    return {
      ok: false,
      message: `Something went wrong starting the radio. Probably a network hiccup. Try again, meatbag.`,
    };
  }
}

/**
 * Stop the radio and leave the voice channel
 * @param {string} guildId — Discord guild ID
 * @returns {{ok: boolean, message: string}}
 */
export function stopRadio(guildId) {
  const state = guildPlayers.get(guildId);
  if (!state || !state.connection) {
    return { ok: false, message: "I'm not playing anything right now. Turn your own speakers off." };
  }

  try {
    cleanup(guildId);
    return { ok: true, message: "📻 Radio stopped. Back to silence." };
  } catch (err) {
    logger.error(`Failed to stop radio in guild ${guildId}: ${err.message}`);
    return { ok: false, message: "Couldn't stop cleanly. Blame the drivers." };
  }
}

/**
 * Get current playback info for a guild
 * @param {string} guildId — Discord guild ID
 * @returns {{playing: boolean, station?: object, startedAt?: number} | null}
 */
export function getCurrentRadio(guildId) {
  const state = guildPlayers.get(guildId);
  if (!state || !state.stationId) return null;

  const station = getStation(state.stationId);
  return {
    playing: state.player?.state?.status === AudioPlayerStatus.Playing,
    station,
    startedAt: state.startedAt,
  };
}

/**
 * Change volume (0.0 – 1.0)
 * @param {string} guildId
 * @param {number} volume
 */
export function setVolume(guildId, volume) {
  const state = guildPlayers.get(guildId);
  if (!state || !state.player) return false;

  const clamped = Math.max(0, Math.min(1, volume));
  const resource = state.player.state.resource;
  if (resource && resource.volume) {
    resource.volume.setVolume(clamped);
    return true;
  }
  return false;
}

/**
 * Clean up a guild's voice resources
 * @param {string} guildId
 */
function cleanup(guildId) {
  const state = guildPlayers.get(guildId);
  if (!state) return;

  if (state.subscription) {
    state.subscription.unsubscribe();
    state.subscription = null;
  }

  if (state.player) {
    state.player.stop();
  }

  if (state.connection) {
    try {
      state.connection.destroy();
    } catch (e) {
      // ignore
    }
    state.connection = null;
  }

  guildPlayers.delete(guildId);
  logger.info(`Cleaned up radio in guild ${guildId}`);
}

/**
 * Check if Packy is currently playing radio in a guild
 * @param {string} guildId
 */
export function isPlaying(guildId) {
  const state = guildPlayers.get(guildId);
  if (!state || !state.player) return false;
  return state.player.state.status === AudioPlayerStatus.Playing;
}

/**
 * Handle process shutdown gracefully
 */
export function shutdownAllRadio() {
  for (const guildId of guildPlayers.keys()) {
    cleanup(guildId);
  }
}
