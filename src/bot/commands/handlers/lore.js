import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { computeSnark, computeMood } from '../../character/mood.js';
import { selectLore } from '../../character/loreSelector.js';
import { logger } from '../../logger.js';
import { ERR, withCode } from './errors.js';
import { COLORS } from './_shared.js';

export async function handleLoreCommand(interaction, modules) {
  const { lorebook, conceptGraphData, categoryConceptsData } = modules;

  try {
    const topic = interaction.options.getString('topic');

    const snarkLevel = computeSnark(0, 20);
    const mood = computeMood(snarkLevel);

    const loreEntries = selectLore(lorebook, topic || 'general', mood, 2, conceptGraphData, categoryConceptsData);

    if (!loreEntries || loreEntries.length === 0) {
      return await interaction.editReply('Packy has no memories matching that topic, meatbag.');
    }

    let categoryName = 'Archives';
    if (lorebook.categories) {
      for (const [catName, entries] of Object.entries(lorebook.categories)) {
        if (Array.isArray(entries) && entries.some(e => loreEntries.includes(e))) {
          categoryName = catName;
          break;
        }
      }
    }

    const embed = new EmbedBuilder()
      .setTitle('Packy Remembers...')
      .setColor(0x4a4a4a)
      .setDescription(loreEntries.join('\n\n'))
      .setFooter({ text: categoryName });

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Error handling /lore command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.LORE, 'Something broke in my circuits. Very embarrassing.'));
    } catch { /* non-fatal */ }
  }
}

export async function handleWarCommand(interaction, modules) {
  const { lorebook } = modules;

  try {
    const allEntries = [];

    if (lorebook.categories) {
      for (const [category, entries] of Object.entries(lorebook.categories)) {
        if (category.toLowerCase().includes('war') && Array.isArray(entries)) {
          allEntries.push(...entries);
        }
      }
    }

    let warStory;
    if (allEntries.length > 0) {
      warStory = allEntries[Math.floor(Math.random() * allEntries.length)];
    } else {
      const allCategoryEntries = [];
      if (lorebook.categories) {
        for (const entries of Object.values(lorebook.categories)) {
          if (Array.isArray(entries)) {
            allCategoryEntries.push(...entries);
          }
        }
      }

      if (allCategoryEntries.length === 0) {
        return await interaction.editReply('No war stories in my memory banks. How peaceful.');
      }

      warStory = allCategoryEntries[Math.floor(Math.random() * allCategoryEntries.length)];
    }

    const warButton = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('war_another')
        .setLabel('Another one')
        .setStyle(ButtonStyle.Danger)
    );

    const embed = new EmbedBuilder()
      .setTitle('War Story')
      .setColor(COLORS.WAR)
      .setDescription(warStory)
      .setFooter({ text: "From the archives of Packy's trauma" })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed], components: [warButton] });
  } catch (error) {
    logger.error('Error handling /war command:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.LORE, 'Something broke in my circuits. Very embarrassing.'));
    } catch { /* non-fatal */ }
  }
}

export async function handleWarButton(interaction, modules) {
  const { lorebook } = modules;

  try {
    await interaction.deferUpdate();

    const allEntries = [];
    if (lorebook && lorebook.categories) {
      for (const [category, entries] of Object.entries(lorebook.categories)) {
        if (category.toLowerCase().includes('war') && Array.isArray(entries)) {
          allEntries.push(...entries);
        }
      }
    }

    if (allEntries.length === 0 && lorebook && lorebook.categories) {
      for (const entries of Object.values(lorebook.categories)) {
        if (Array.isArray(entries)) allEntries.push(...entries);
      }
    }

    if (allEntries.length === 0) {
      return await interaction.editReply({ content: 'Memory banks empty.', embeds: [], components: [] });
    }

    const warStory = allEntries[Math.floor(Math.random() * allEntries.length)];

    const warButton = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('war_another')
        .setLabel('Another one')
        .setStyle(ButtonStyle.Danger)
    );

    const embed = new EmbedBuilder()
      .setTitle('War Story')
      .setColor(COLORS.WAR)
      .setDescription(warStory)
      .setFooter({ text: "From the archives of Packy's trauma" })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed], components: [warButton] });
  } catch (error) {
    logger.error('Error handling war button:', { error: error instanceof Error ? error.message : error });
    try {
      await interaction.editReply(withCode(ERR.LORE, 'War story engine misfired.'));
    } catch { /* non-fatal */ }
  }
}
