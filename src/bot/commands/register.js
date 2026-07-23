// @ts-nocheck — TODO: add types
import { REST, Routes, SlashCommandBuilder, PermissionFlagsBits } from 'discord.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;

if (!DISCORD_TOKEN || !DISCORD_CLIENT_ID) {
  console.error('Error: DISCORD_TOKEN and DISCORD_CLIENT_ID must be set in .env');
  process.exit(1);
}

// Define slash commands
const commands = [
  new SlashCommandBuilder()
    .setName('packy')
    .setDescription('Talk to Packy')
    .addStringOption((option) =>
      option.setName('message').setDescription('What do you want to ask Packy?').setRequired(true),
    ),

  new SlashCommandBuilder().setName('mood').setDescription("Show Packy's current mood state"),

  new SlashCommandBuilder()
    .setName('lore')
    .setDescription('Packy tells a lore story about a topic')
    .addStringOption((option) =>
      option
        .setName('topic')
        .setDescription('What topic should Packy tell a story about?')
        .setRequired(true),
    ),

  new SlashCommandBuilder().setName('war').setDescription('Packy tells a random war story'),

  new SlashCommandBuilder()
    .setName('snark')
    .setDescription('Get a snark line from Packy')
    .addStringOption((option) =>
      option
        .setName('category')
        .setDescription('Snark category (default: random mix)')
        .setRequired(false)
        .addChoices(
          { name: 'Random mix', value: 'random' },
          { name: 'Base', value: 'base' },
          { name: 'Lore', value: 'lore' },
          { name: 'Chromebook', value: 'chromebook' },
          { name: 'Tech humor', value: 'tech_humor' },
          { name: 'Code comments', value: 'code_comments' },
        ),
    ),

  new SlashCommandBuilder().setName('status').setDescription('Show Packy system status'),

  new SlashCommandBuilder().setName('chaos').setDescription('Show chaos state for this channel'),

  new SlashCommandBuilder().setName('help').setDescription('List all Packy commands'),

  new SlashCommandBuilder()
    .setName('radio')
    .setDescription('Play Danish and international radio in voice chat')
    .addSubcommand((subcommand) =>
      subcommand
        .setName('play')
        .setDescription('Join voice channel and start playing radio')
        .addStringOption((option) =>
          option
            .setName('station')
            .setDescription('Station ID (e.g. drp3, nova, voice, drp8)')
            .setRequired(true),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand.setName('stop').setDescription('Stop radio and leave voice channel'),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('stations')
        .setDescription('List available radio stations')
        .addStringOption((option) =>
          option
            .setName('category')
            .setDescription('Filter by category')
            .setRequired(false)
            .addChoices(
              { name: 'DR (Danish Public)', value: 'DR' },
              { name: 'Commercial', value: 'Commercial' },
              { name: 'International', value: 'International' },
            ),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('nowplaying')
        .setDescription('Show what radio station is currently playing'),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('volume')
        .setDescription('Adjust radio volume')
        .addIntegerOption((option) =>
          option
            .setName('level')
            .setDescription('Volume 0–100')
            .setRequired(true)
            .setMinValue(0)
            .setMaxValue(100),
        ),
    ),

  new SlashCommandBuilder()
    .setName('admin')
    .setDescription('Admin controls for Packy')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addSubcommand((subcommand) =>
      subcommand.setName('mute').setDescription('Silence Packy in this server'),
    )
    .addSubcommand((subcommand) =>
      subcommand.setName('unmute').setDescription('Let Packy speak again'),
    )
    .addSubcommand((subcommand) =>
      subcommand.setName('chaos-on').setDescription('Enable chaos/unprovoked commentary'),
    )
    .addSubcommand((subcommand) =>
      subcommand.setName('chaos-off').setDescription('Disable chaos/unprovoked commentary'),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('allow-channel')
        .setDescription('Allow Packy to speak in a specific channel')
        .addStringOption((option) =>
          option.setName('channel_id').setDescription('Channel ID to allow').setRequired(true),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('clear-channels')
        .setDescription('Reset channel restrictions (allow all channels)'),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('set-location')
        .setDescription('Set the city Packy checks weather for in this server')
        .addStringOption((option) =>
          option
            .setName('city')
            .setDescription('City name (e.g. "New York", "Tokyo", "London")')
            .setRequired(true),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('character')
        .setDescription('Switch active personality')
        .addStringOption((option) =>
          option
            .setName('name')
            .setDescription('Character name: Vernon, KRONOS, Glitch, Sunjinwo, Packy')
            .setRequired(true),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('family-friendly')
        .setDescription('Toggle family-friendly mode (sanitized snark)')
        .addBooleanOption((option) =>
          option
            .setName('enabled')
            .setDescription('Enable (true) or disable (false) family-friendly mode')
            .setRequired(true),
        ),
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('clear-ratelimit')
        .setDescription('Clear rate limit for a specific user (admin override)')
        .addStringOption((option) =>
          option
            .setName('user_id')
            .setDescription('Discord user ID to clear rate limit for')
            .setRequired(true),
        ),
    ),
].map((command) => command.toJSON());

// Create REST instance
const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

/**
 * Register slash commands with Discord
 */
async function registerCommands() {
  try {
    console.log('[REGISTER] Starting slash command registration...');
    console.log(`[REGISTER] Registering ${commands.length} command(s)`);

    // Register globally (available in all guilds after 1 hour)
    // For testing, you may want to register to a specific guild instead:
    // const route = Routes.applicationGuildCommands(DISCORD_CLIENT_ID, DISCORD_GUILD_ID);
    const route = Routes.applicationCommands(DISCORD_CLIENT_ID);

    const data = await rest.put(route, { body: commands });

    console.log(`[REGISTER] Successfully registered ${data.length} command(s)`);
    console.log('[REGISTER] Commands:');
    data.forEach((cmd) => {
      console.log(`  - /${cmd.name}: ${cmd.description}`);
    });
    console.log('[REGISTER] Slash commands will be available in all guilds within 1 hour');
  } catch (error) {
    console.error('[REGISTER] Error registering commands:', error);
    process.exit(1);
  }
}

// Run registration
registerCommands();
