import { Client, GatewayIntentBits } from 'discord.js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Import character system modules
import { getCurrentCharacter, processResponse } from './character/randomizer.js';
import { getMixedSnark } from './character/snarkBank.js';
import { loadLorebook, loadConceptGraph } from './character/loreSelector.js';
import { computeSnark, computeMood } from './character/mood.js';
import {
  createChaosState,
  computeChaosScore,
  shouldFireUnprovoked,
  recordInjection,
} from './character/chaosState.js';
import { readSignals } from './signals.js';
import { logger } from './logger.js';
import { withCode, ERR } from './commands/handlers/errors.js';
import { loadChaosState, startAutoSave as startChaosAutoSave, saveChaosState, stopAutoSave as stopChaosAutoSave } from './chaosStatePersist.js';
import { initDb } from './db.js';
import { filterFamilyFriendly } from './character/contentFilter.js';

// ponytail: API adapters live in the Python cognition service (/respond) per
// ADR-003. The JS direct-mode adapter calls were the removed duplicate
// pipeline (ADR-010); no JS adapter imports remain.

// Import shared rate limiter
import { isRateLimited } from './rateLimiter.js';

// Import user state and guild config
import { loadState, updateUserState, startAutoSave as startStateAutoSave, saveState, stopAutoSave as stopStateAutoSave } from './userState.js';
import { loadGuildConfigs, getGuildConfig, isChannelAllowed, isGuildMuted, startAutoSave as startConfigAutoSave, setGuildConfig, saveGuildConfigs, stopAutoSave as stopConfigAutoSave } from './guildConfig.js';

// Import command handlers
import {
  handlePackyCommand,
  handleMoodCommand,
  handleLoreCommand,
  handleWarCommand,
  handleAdminCommand,
  handleSnarkCommand,
  handleStatusCommand,
  handleChaosCommand,
  handleHelpCommand,
  handleWarButton,
  handleRadioPlay,
  handleRadioStop,
  handleRadioStations,
  handleRadioNowPlaying,
  handleRadioVolume,
  handleRadioStationsButton,
} from './commands/handlers.js';
import { RADIO_STATIONS } from './radio/radioStations.js';
import { shutdownAllRadio } from './radio/radioPlayer.js';

// Load environment variables
dotenv.config();

// Get __dirname equivalent in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const BOT_MODE = process.env.BOT_MODE || 'microservice'; // 'microservice' only (direct removed, ADR-010); retained for status logging
const PRIMARY_ADAPTER = process.env.PRIMARY_ADAPTER || 'claude'; // 'claude' or 'minimax'
const COGNITION_PORT = process.env.COGNITION_PORT || 8765;
const MAX_INPUT_CHARS = parseInt(process.env.MAX_INPUT_CHARS || '1500', 10);
const AUTH_SECRET = process.env.PACKY_API_SECRET || '';

// Per-channel chaos state map
const channelChaos = new Map();

// Lorebook storage (loaded on ready)
let lorebook = { categories: {} };
let conceptGraphData = null;
let categoryConceptsData = null;

/**
 * Call the Python microservice endpoint
 * @param {string} userText - The user's message
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 * @returns {Promise<string>} Response text from Packy
 */
async function callMicroservice(userText, guildId, userId, retries = 2) {
  const timeout = 8000;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      
      const headers = { 'Content-Type': 'application/json' };
      if (AUTH_SECRET) headers['Authorization'] = `Bearer ${AUTH_SECRET}`;
      
      const response = await fetch(`http://localhost:${COGNITION_PORT}/respond`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          user_text: userText,
          guild_id: guildId,
          user_id: userId,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!response.ok) {
        logger.error(`Microservice error: ${response.status}`);
        if (attempt < retries) {
          await new Promise(r => setTimeout(r, 200 * Math.pow(2, attempt)));
          continue;
        }
      return withCode(ERR.MICROSERVICE, 'I\'m having trouble thinking right now. Try again in a moment.');
    }

      const data = await response.json();
      return data.result || withCode(ERR.MICROSERVICE, 'Hmm, I got nothing.');
    } catch (error) {
      logger.error(`Microservice attempt ${attempt + 1} failed:`, { error: error.message });
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, 200 * Math.pow(2, attempt)));
        continue;
      }
      if (error.name === 'AbortError') {
        return withCode(ERR.TIMEOUT, 'My brain timed out. Give me a moment to recover.');
      }
      return withCode(ERR.COGNITION_DOWN, 'My brain is offline. Check if the cognition service is running.');
    }
  }
  return withCode(ERR.COGNITION_DOWN, 'My brain is offline. Check if the cognition service is running.');
}

// ponytail: callDirect (the JS-side full cognition pipeline + direct adapter
// call) was the duplicate LLM path. Removed per ADR-003/010 — the Python
// cognition service /respond is the single LLM call path; callMicroservice is
// the only caller. WithCode/ERR/readSignals etc. remain used by
// callMicroservice, the chaos hook, and the modules export below.

/**
 * Main handler for incoming messages
 * Processes directed messages and implements chaos unprovoked commentary hook
 * @param {Message} message - Discord message object
 */
async function handleMessage(message) {
  trackInFlight(1);
  // Ignore bot messages and own messages
  if (message.author.bot || message.author.id === message.client.user.id) {
    return;
  }

  // CHAOS UNPROVOKED COMMENTARY HOOK
  // Fire on ALL messages (even ones not directed at Packy) with guardrails
  if (message.guild && message.guild.id && !message.author.bot) {
    try {
      // Get/create chaos state for this channel
      if (!channelChaos.has(message.channelId)) {
        channelChaos.set(message.channelId, createChaosState());
      }
      const chaosState = channelChaos.get(message.channelId);

      // Compute chaos score from a generic state
      const snarkLevel = computeSnark(0, 20);
      const mood = computeMood(snarkLevel);
      const chaosScore = computeChaosScore(mood, snarkLevel);

      // Check guild config guards for chaos
      const guildCfg = getGuildConfig(message.guildId);
      if (guildCfg.chaosEnabled && guildCfg.unprovokedEnabled) {
        // Check if should fire unprovoked
        if (shouldFireUnprovoked(chaosState, message.channelId, chaosScore)) {
          // Pick random snark line
          const snarkLine = getMixedSnark(1)[0];

          // Send to channel (not as reply)
          try {
            await message.channel.send(snarkLine);
            recordInjection(message.channelId);
          } catch (e) {
            logger.warn('Failed to send unprovoked commentary', { error: e.message });
          }
        }
      }
    } catch (e) {
      // Silently fail unprovoked commentary - don't interrupt normal flow
      logger.warn('Unprovoked commentary error', { error: e.message });
    }
  }

  // Check if bot is mentioned or message starts with !packy prefix
  const isMentioned = message.mentions.has(message.client.user);
  const isPrefix = message.content.startsWith('!packy');

  if (!isMentioned && !isPrefix) {
    return;
  }

  // Check guild mute and channel allow settings
  if (message.guildId && isGuildMuted(message.guildId)) return;
  if (message.guildId && !isChannelAllowed(message.guildId, message.channelId)) return;

  // Check rate limit
  if (await isRateLimited(message.author.id)) {
    return message.reply({
      content: 'Slow down meatbag. Even I need a moment.',
      allowedMentions: { repliedUser: false },
    });
  }

  // Show typing indicator
  try {
    await message.channel.sendTyping();
  } catch { /* non-fatal: typing indicator */ }

  // Extract user text (remove mention or prefix)
  let userText = message.content.trim();
  if (isMentioned) {
    userText = userText
      .replace(/<@!?\d+>/g, '') // Remove mention
      .trim();
  } else if (isPrefix) {
    userText = userText.replace(/^!packy\s*/i, '').trim();
  }

  if (!userText) {
    return message.reply({
      content: 'You gonna say something, or are we just staring at each other?',
      allowedMentions: { repliedUser: false },
    });
  }

  // Cap input length before LLM dispatch
  if (userText.length > MAX_INPUT_CHARS) {
    userText = userText.substring(0, MAX_INPUT_CHARS);
    logger.warn('Input truncated', { original: message.content.length, max: MAX_INPUT_CHARS });
    try {
      await message.reply({
        content: `Your message was trimmed to ${MAX_INPUT_CHARS} characters before I processed it.`,
        allowedMentions: { repliedUser: false },
      });
    } catch { /* non-fatal */ }
  }

  try {
    // ponytail: single LLM call path — Python cognition /respond (ADR-003/010).
    let response = await callMicroservice(userText, message.guildId, message.author.id);

    // Process response (Glitch may corrupt output)
    let processedResponse = processResponse(response);

    // Apply family-friendly filter if enabled for this guild
    if (message.guildId) {
      const guildCfg = getGuildConfig(message.guildId);
      if (guildCfg.familyFriendly) {
        processedResponse = filterFamilyFriendly(processedResponse, getCurrentCharacter()?.name);
      }
    }

    if (processedResponse.length > 1990) {
      response = processedResponse.substring(0, 1990) + '...';
    } else {
      response = processedResponse;
    }

    await message.reply({
      content: response,
      allowedMentions: { repliedUser: false },
    });

    // Update user state after successful reply (single call = +1 interaction count)
    try {
      if (message.guildId) {
        updateUserState(message.guildId, message.author.id, {});
      }
    } catch { /* non-fatal */ }

    return;
  } catch (error) {
    logger.error('Error handling message', { error: error instanceof Error ? error.message : error });
    return message.reply({
      content: withCode(ERR.UNKNOWN, 'Something broke in my circuits. Very embarrassing.'),
      allowedMentions: { repliedUser: false },
    });
  } finally {
    trackInFlight(-1);
  }
}

/**
 * Main handler for Discord interactions (slash commands)
 * Delegates to command handlers in commands/handlers.js
 * @param {Interaction} interaction - Discord interaction object
 */
async function handleInteraction(interaction) {
  trackInFlight(1);
  // Shared modules for all handlers
  const modules = {
    lorebook,
    conceptGraphData,
    categoryConceptsData,
    channelChaos,
    callMicroservice,
    readSignals,
    getGuildConfig,
    setGuildConfig,
    saveGuildConfigs,
    updateUserState,
  };

  // Button interactions
  if (interaction.isButton()) {
    if (interaction.customId === 'war_another') {
      return await handleWarButton(interaction, modules);
    }
    if (interaction.customId.startsWith('radio_stn_page:')) {
      // Re-derive stations list for pagination context
      // The customId stores: radio_stn_page:{page}
      // We use the most recent category from the stored interaction context
      const stations = RADIO_STATIONS;
      return await handleRadioStationsButton(interaction, stations, null);
    }
    return;
  }

  if (!interaction.isChatInputCommand()) {
    return;
  }

  try {
    await interaction.deferReply();

    // Guard: 14-minute timeout to avoid dead thinking state
    const handlerPromise = (async () => {
      const command = interaction.commandName;

      if (command === 'packy')  return await handlePackyCommand(interaction, modules);
      if (command === 'mood')   return await handleMoodCommand(interaction, modules);
      if (command === 'lore')   return await handleLoreCommand(interaction, modules);
      if (command === 'war')    return await handleWarCommand(interaction, modules);
      if (command === 'admin')  return await handleAdminCommand(interaction, modules);
      if (command === 'snark')  return await handleSnarkCommand(interaction, modules);
      if (command === 'status') return await handleStatusCommand(interaction, modules);
      if (command === 'chaos')  return await handleChaosCommand(interaction, modules);
      if (command === 'help')   return await handleHelpCommand(interaction, modules);

      // Radio commands
      if (command === 'radio') {
        const sub = interaction.options.getSubcommand();
        if (sub === 'play')       return await handleRadioPlay(interaction);
        if (sub === 'stop')       return await handleRadioStop(interaction);
        if (sub === 'stations')   return await handleRadioStations(interaction);
        if (sub === 'nowplaying') return await handleRadioNowPlaying(interaction);
        if (sub === 'volume')     return await handleRadioVolume(interaction);
      }

      return await interaction.editReply('This command is not yet implemented.');
    })();

    const TIMEOUT_MS = 14 * 60 * 1000;
    await Promise.race([
      handlerPromise,
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Command handler timed out')), TIMEOUT_MS)
      ),
    ]);
  } catch (error) {
    logger.error('Error handling interaction', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.UNKNOWN, 'Something broke in my circuits. Very embarrassing.'));
    } catch { /* non-fatal: reply already failed */ }
  } finally {
    trackInFlight(-1);
  }
}

// Initialize Discord client
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

// Ready event - load lorebook and initialize
client.on('ready', async () => {
  const activeCharacter = getCurrentCharacter();
  logger.info('Bot ready', { 
    tag: client.user.tag, 
    guilds: client.guilds.cache.size, 
    mode: BOT_MODE,
    adapter: PRIMARY_ADAPTER,
    personality: activeCharacter?.name,
    personalityDesc: activeCharacter?.description,
  });

  if (BOT_MODE === 'microservice') {
    logger.info('Cognition service config', { port: COGNITION_PORT, authConfigured: !!AUTH_SECRET });
  }

  // Load lorebook for active character
  const lorePath = activeCharacter?.lorePath || 'data/lorebook/packy_lorebook_structured.json';
  try {
    const loreBookAbsPath = path.resolve(__dirname, lorePath);
    logger.info('Loading lorebook', { path: loreBookAbsPath });
    lorebook = await loadLorebook(loreBookAbsPath);
    logger.info('Lorebook loaded', { categories: Object.keys(lorebook.categories).length });
  } catch (error) {
    logger.error('Failed to load lorebook', { error: error.message });
    lorebook = { categories: {} };
  }

  // Load concept graph and category concepts
  try {
    const conceptGraphPath = path.resolve(__dirname, 'data/lorebook/concept_graph.json');
    const categoryConceptsPath = path.resolve(__dirname, 'data/lorebook/category_concepts.json');
    const conceptData = await loadConceptGraph(conceptGraphPath, categoryConceptsPath);
    conceptGraphData = conceptData.conceptGraph;
    categoryConceptsData = conceptData.categoryConceptsMap;
    logger.info('Concept graph loaded', { graphKeys: Object.keys(conceptGraphData).length, categoryConcepts: Object.keys(categoryConceptsData).length });
  } catch (error) {
    logger.error('Failed to load concept graph', { error: error.message });
    conceptGraphData = {};
    categoryConceptsData = {};
  }

  // Initialize SQLite state store (must be first — creates tables + migrates JSON)
  initDb();

  // Load chaos state persistence
  await loadChaosState();
  startChaosAutoSave();
  logger.info('Chaos state persistence loaded');

  // Load user state and guild configs
  await loadState();
  await loadGuildConfigs();
  startStateAutoSave();
  startConfigAutoSave();
  logger.info('User state and guild config loaded');
});

// Message create event
client.on('messageCreate', handleMessage);

// Interaction create event
client.on('interactionCreate', handleInteraction);

// Graceful shutdown
let _shuttingDown = false;
let _inFlightCount = 0;

export function trackInFlight(delta = 1) {
  _inFlightCount += delta;
}

async function gracefulShutdown(signal) {
  if (_shuttingDown) return;
  _shuttingDown = true;
  logger.info(`Received ${signal}, powering down`);

  // Stop accepting new work
  shutdownAllRadio();
  stopStateAutoSave();
  stopConfigAutoSave();
  stopChaosAutoSave();

  // Wait for in-flight operations with 5s deadline
  const deadline = Date.now() + 5000;
  while (_inFlightCount > 0 && Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 100));
  }
  if (_inFlightCount > 0) {
    logger.warn('Proceeding to shutdown with in-flight operations', { count: _inFlightCount });
  }

  // Flush pending saves
  try { await saveGuildConfigs(); } catch { /* non-fatal */ }
  try { await saveState(); } catch { /* non-fatal */ }
  try { await saveChaosState(); } catch { /* non-fatal */ }

  await client.destroy();
  process.exit(0);
}

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

// Alert handler — surface threshold breaches to an ops channel
logger.on('alert', (payload) => {
  logger.error('ALERT', payload);
  // In production, post to a Discord ops channel or webhook
});

// Error handling
client.on('error', (error) => {
  logger.error('Discord client error', { error: error.message, stack: error.stack });
});

let unhandledRejectionCount = 0;
const REJECTION_ALERT_THRESHOLD = 5;
process.on('unhandledRejection', (reason, _promise) => {
  unhandledRejectionCount++;
  logger.error('Unhandled rejection', { 
    reason: reason instanceof Error ? reason.message : String(reason),
    stack: reason instanceof Error ? reason.stack : null,
    count: unhandledRejectionCount,
  });
  if (unhandledRejectionCount === REJECTION_ALERT_THRESHOLD) {
    logger.emit && logger.emit('alert', {
      type: 'unhandledRejectionThreshold',
      message: `${REJECTION_ALERT_THRESHOLD} unhandled rejections reached — investigate memory leaks or dangling promises`,
      count: unhandledRejectionCount,
    });
  }
});

// Start the bot
client.login(DISCORD_TOKEN);
