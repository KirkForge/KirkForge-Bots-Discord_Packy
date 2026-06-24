import { Client, GatewayIntentBits } from 'discord.js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Import character system modules
import { getCurrentPrompt, getCurrentState, getCurrentCharacter, selectCharacterByName, selectRandomCharacter, getSnark, processResponse, listCharacters } from './character/randomizer.js';
import { getMixedSnark } from './character/snarkBank.js';
import { loadLorebook, selectLore } from './character/loreSelector.js';
import { PackyState } from './character/state.js'; // kept for legacy compat
import { buildSystemPrompt, getResponseStyleLimit } from './character/systemPrompt.js';
import { computeSnark, computeMood } from './character/mood.js';
import { extractKeywords } from './character/keywords.js';
import {
  createChaosState,
  computeChaosScore,
  applyMoodOverride,
  shouldFireUnprovoked,
  recordInjection,
} from './character/chaosState.js';
import { readSignals } from './signals.js';
import { logger, getCorrelationId } from './logger.js';
import { loadChaosState, startAutoSave as startChaosAutoSave } from './chaosStatePersist.js';
import { filterFamilyFriendly } from './character/contentFilter.js';

// Import API adapters
import { callWithRetry as callClaude } from './api/claudeAdapter.js';
import { callWithRetry as callMiniMax } from './api/minimaxAdapter.js';

// Import shared rate limiter
import { isRateLimited } from './rateLimiter.js';

// Import user state and guild config
import { loadState, updateUserState, startAutoSave as startStateAutoSave } from './userState.js';
import { loadGuildConfigs, getGuildConfig, isChannelAllowed, isGuildMuted, startAutoSave as startConfigAutoSave, setGuildConfig, saveGuildConfigs } from './guildConfig.js';

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
} from './commands/handlers.js';
import { shutdownAllRadio } from './radio/radioPlayer.js';

// Load environment variables
dotenv.config();

// Get __dirname equivalent in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const BOT_MODE = process.env.BOT_MODE || 'microservice'; // 'direct' or 'microservice'
const PRIMARY_ADAPTER = process.env.PRIMARY_ADAPTER || 'claude'; // 'claude' or 'minimax'
const COGNITION_PORT = process.env.COGNITION_PORT || 8765;
const LOREBOOK_PATH = process.env.LOREBOOK_PATH || 'data/lorebook/packy_lorebook_structured.json';
const MAX_INPUT_CHARS = parseInt(process.env.MAX_INPUT_CHARS || '1500', 10);
const AUTH_SECRET = process.env.PACKY_API_SECRET || '';

// Per-channel chaos state map
const channelChaos = new Map();

// Lorebook storage (loaded on ready)
let lorebook = { categories: {} };

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
        console.error(`Microservice error: ${response.status}`);
        if (attempt < retries) {
          await new Promise(r => setTimeout(r, 200 * Math.pow(2, attempt)));
          continue;
        }
        return 'I\'m having trouble thinking right now. Try again in a moment.';
      }

      const data = await response.json();
      return data.result || 'Hmm, I got nothing.';
    } catch (error) {
      console.error(`Microservice attempt ${attempt + 1} failed:`, error.message);
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, 200 * Math.pow(2, attempt)));
        continue;
      }
      if (error.name === 'AbortError') {
        return 'My brain timed out. Give me a moment to recover.';
      }
      return 'My brain is offline. Check if the cognition service is running.';
    }
  }
  return 'My brain is offline. Check if the cognition service is running.';
}

/**
 * Call the API directly with real implementation
 * Builds state, selects lore, constructs system prompt, and calls chosen adapter
 * @param {string} userText - The user's message
 * @param {string} guildId - Discord guild ID
 * @param {string} userId - Discord user ID
 * @returns {Promise<{text: string, state: object}>} Response text and Packy state
 */
async function callDirect(userText, _guildId, _userId) {
  try {
    // Read live signals (CPU + weather)
    const signals = await readSignals(
      process.env.OPENWEATHER_API_KEY,
      process.env.PACKY_LOCATION || 'London'
    );

    // Use active character state (from randomizer)
    const characterName = getCurrentCharacter()?.name || 'Packy';
    let state = getCurrentState();
    
    // Fallback to PackyState if needed (shouldn't happen after randomizer init)
    if (!state) {
      state = new PackyState();
    }

    // Character-specific signal processing
    const snarkLevel = computeSnark(signals.cpu, signals.temp ?? 20);
    const mood = computeMood(snarkLevel);
    const keywords = extractKeywords(userText);

    state.turn++;
    state.snark = snarkLevel;
    state.mood = mood;
    state.keywords = keywords;
    state.cpu = signals.cpu;
    state.temp = signals.temp;
    state.weather = signals.weather;

    // Select lore entries using character-specific lorebook
    const loreEntries = selectLore(lorebook, userText, mood, 2);

    // Get snark lines
    const snarkLines = getMixedSnark(2);

    // Build system prompt using active character
    const systemPrompt = getCurrentPrompt(loreEntries.map(text => ({ text })), snarkLines);

    // Apply mood override to response length
    const responseStyleLimit = getResponseStyleLimit(mood);
    const maxChars = applyMoodOverride(mood, responseStyleLimit.maxChars);

    // Call adapter based on PRIMARY_ADAPTER env var
    let result;
    if (PRIMARY_ADAPTER === 'minimax') {
      result = await callMiniMax(systemPrompt, userText, { maxTokens: maxChars });
    } else {
      // Default to claude
      result = await callClaude(systemPrompt, userText, { maxTokens: maxChars });
    }

    return { text: result.text || 'I got nothing.', state };
  } catch (error) {
    console.error('Direct API call failed:', error.message);
    return { text: 'API call crashed. How typical.', state: null };
  }
}

/**
 * Main handler for incoming messages
 * Processes directed messages and implements chaos unprovoked commentary hook
 * @param {Message} message - Discord message object
 */
async function handleMessage(message) {
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
            console.error('Failed to send unprovoked commentary:', e.message);
          }
        }
      }
    } catch (e) {
      // Silently fail unprovoked commentary - don't interrupt normal flow
      console.error('Unprovoked commentary error:', e.message);
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
  if (isRateLimited(message.author.id)) {
    return message.reply({
      content: 'Slow down meatbag. Even I need a moment.',
      allowedMentions: { repliedUser: false },
    });
  }

  // Show typing indicator
  try {
    await message.channel.sendTyping();
  } catch {
    // silently fail typing indicator
  }

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
    console.log(`[PACKY] Input truncated from ${message.content.length} to ${MAX_INPUT_CHARS} chars`);
  }

  try {
    let response;
    let packyState = null;

    if (BOT_MODE === 'direct') {
      const result = await callDirect(userText, message.guildId, message.author.id);
      response = result.text;
      packyState = result.state;
    } else {
      // default to microservice mode
      response = await callMicroservice(userText, message.guildId, message.author.id);
    }

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
        const stateUpdate = packyState ? { mood_history: [packyState.mood] } : {};
        updateUserState(message.guildId, message.author.id, stateUpdate);
      }
    } catch { /* non-fatal */ }

    return;
  } catch (error) {
    console.error('Error handling message:', error);
    return message.reply({
      content: 'Something broke in my circuits. Very embarrassing.',
      allowedMentions: { repliedUser: false },
    });
  }
}

/**
 * Main handler for Discord interactions (slash commands)
 * Delegates to command handlers in commands/handlers.js
 * @param {Interaction} interaction - Discord interaction object
 */
async function handleInteraction(interaction) {
  // Shared modules for all handlers
  const modules = {
    lorebook,
    channelChaos,
    callDirect,
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
    return;
  }

  if (!interaction.isChatInputCommand()) {
    return;
  }

  try {
    await interaction.deferReply();

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
  } catch (error) {
    console.error('Error handling interaction:', error);
    try {
      await interaction.editReply('Something broke in my circuits. Very embarrassing.');
    } catch {
      // Silently fail if can't edit reply
    }
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
process.on('SIGINT', async () => {
  logger.info('Received SIGINT, powering down');
  shutdownAllRadio();
  await client.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  logger.info('Received SIGTERM, powering down');
  shutdownAllRadio();
  await client.destroy();
  process.exit(0);
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
