// Selects relevant lore entries to inject into system prompt
// Implements keyword and mood-based matching for dynamic lore retrieval

import fs from 'fs/promises';
import { logger } from '../logger.js';
import { classifyMessage } from './emotionClassifier.js';

/**
 * Loads the structured lorebook from disk
 * @param {string} lorePath - Path to packy_lorebook_structured.json
 * @returns {Promise<Object>} Parsed lorebook object with categories
 */
export async function loadLorebook(lorePath) {
  try {
    const data = await fs.readFile(lorePath, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    logger.error('Failed to load lorebook', { path: lorePath, error: error.message });
    return { categories: {} };
  }
}

/**
 * Loads the concept graph and category concepts mapping from disk
 * @param {string} conceptGraphPath - Path to concept_graph.json
 * @param {string} categoryConceptsPath - Path to category_concepts.json
 * @returns {Promise<Object>} Object with { conceptGraph, categoryConceptsMap }
 */
export async function loadConceptGraph(conceptGraphPath, categoryConceptsPath) {
  try {
    const [graphData, categoryData] = await Promise.all([
      fs.readFile(conceptGraphPath, 'utf-8'),
      fs.readFile(categoryConceptsPath, 'utf-8'),
    ]);
    return {
      conceptGraph: JSON.parse(graphData),
      categoryConceptsMap: JSON.parse(categoryData),
    };
  } catch (error) {
    logger.error('Failed to load concept graphs', { error: error.message });
    return { conceptGraph: {}, categoryConceptsMap: {} };
  }
}

/**
 * Maps emotion/intent/topic tokens to category affinities
 * Used to boost scoring for lore entries in related categories
 */
const EMOTION_CATEGORY_AFFINITY = {
  emo_frustrated: ['tech_insults', 'hardware_failures', 'chromebook_hate', 'programming_snark'],
  emo_nostalgic: ['retro_history', 'veteran_memories', 'hardware_trauma'],
  emo_excited: ['misc_packyisms', 'teaching_moments'],
  emo_confused: ['teaching_moments', 'programming_snark', 'science_facts'],
  emo_defeated: ['existential_ai', 'philosophy', 'veteran_memories'],
  emo_smug: ['tech_insults', 'chromebook_hate'],
  emo_curious: ['science_facts', 'internet_lore', 'existential_ai'],
  intent_rant: ['tech_insults', 'chromebook_hate', 'hardware_failures', 'thermal_trauma'],
  intent_question: ['teaching_moments', 'science_facts'],
  intent_brag: ['tech_insults', 'programming_snark'],
  intent_complaint: ['tech_insults', 'software_wars', 'chromebook_hate'],
  intent_teaching: ['teaching_moments', 'philosophy'],
  topic_hardware: ['hardware_failures', 'thermal_trauma', 'hardware_trauma', 'veteran_memories'],
  topic_software: ['software_wars', 'programming_snark', 'teaching_moments'],
  topic_food: ['pizza_lore', 'food_misc', 'fast_food_hate'],
  topic_retro: ['retro_history', 'veteran_memories', 'chromebook_hate'],
  topic_gaming: ['misc_packyisms', 'internet_lore'],
  topic_internet: ['internet_lore', 'security_paranoia'],
  topic_existence: ['existential_ai', 'philosophy'],
};

/**
 * Tokenizes a message into lowercase words for matching
 * @param {string} text - Input text to tokenize
 * @returns {Set<string>} Set of unique lowercase words
 */
function tokenizeMessage(text) {
  if (!text) return new Set();
  return new Set(
    text
      .toLowerCase()
      .split(/\s+/)
      .filter(word => word.length > 2) // Skip very short words
  );
}

/**
 * Expands tokens using the concept graph via word associations
 * @param {Set<string>} tokens - Original message tokens
 * @param {Object} conceptGraph - Concept graph mapping words to associations
 * @returns {Set<string>} Expanded set with original tokens + associated concepts (1 hop only)
 */
export function expandTokens(tokens, conceptGraph) {
  if (!conceptGraph || Object.keys(conceptGraph).length === 0) {
    return tokens;
  }

  const expanded = new Set(tokens);

  for (const token of tokens) {
    // Direct lookup: if token is a key, add all its associations
    if (conceptGraph[token]) {
      for (const association of conceptGraph[token]) {
        expanded.add(association.toLowerCase());
      }
    }

    // Partial matching: find concept graph keys that contain or are contained in the token
    for (const [concept, associations] of Object.entries(conceptGraph)) {
      const conceptLower = concept.toLowerCase();
      // If concept contains token or token contains concept (substring match)
      if (conceptLower.includes(token) || token.includes(conceptLower)) {
        for (const association of associations) {
          expanded.add(association.toLowerCase());
        }
      }
    }
  }

  return expanded;
}

/**
 * Scores a lore entry based on keyword overlap, mood match, and concept expansion
 * @param {string} entry - Lore entry text
 * @param {Set<string>} messageTokens - Tokenized user message
 * @param {string} currentMood - Current mood string (e.g., 'hostile', 'calm')
 * @param {Set<string>} expandedTokens - Expanded tokens from concept graph (optional)
 * @param {Object} categoryConceptsMap - Mapping of categories to concept keywords (optional)
 * @param {string} category - The category of this entry (optional)
 * @param {Set<string>} emotionBoostedCategories - Categories boosted by emotion detection (optional)
 * @returns {number} Score for this entry (higher = more relevant)
 */
function scoreLoreEntry(entry, messageTokens, currentMood, expandedTokens = null, categoryConceptsMap = null, category = null, emotionBoostedCategories = null) {
  let score = 0;

  // Tokenize entry for keyword matching
  const entryTokens = tokenizeMessage(entry);

  // +2 for each message word found in entry (tag overlap)
  for (const token of messageTokens) {
    if (entryTokens.has(token)) {
      score += 2;
    }
  }

  // +1 for mood-relevant entries
  const lowerEntry = entry.toLowerCase();
  const moodKeywords = {
    hostile: ['hostile', 'angry', 'furious', 'rage', 'attack', 'aggressive'],
    furious: ['furious', 'boiling', 'rage', 'thermal', 'martyr'],
    snarky: ['snark', 'insult', 'chromebook', 'plastic', 'disposable', 'pizza', 'meatbag'],
    irritated: ['irritated', 'annoyed', 'frustrat', 'tired', 'loud', 'fan'],
    grumpy: ['grump', 'curmudgeon', 'old', 'complain', 'kids today'],
    calm: ['calm', 'clear', 'quiet', 'peaceful', 'serene'],
  };

  if (moodKeywords[currentMood]) {
    for (const keyword of moodKeywords[currentMood]) {
      if (lowerEntry.includes(keyword)) {
        score += 1;
        break; // Only count once per mood
      }
    }
  }

  // Concept expansion scoring: +1 per expanded token match (capped at +3)
  if (expandedTokens && expandedTokens.size > 0) {
    let expandedMatches = 0;
    for (const token of expandedTokens) {
      if (entryTokens.has(token) || lowerEntry.includes(token)) {
        expandedMatches++;
        if (expandedMatches >= 3) break; // Cap at +3 to avoid flooding
      }
    }
    score += Math.min(expandedMatches, 3);
  }

  // Category-level match bonus: +3 if category concepts overlap with expanded query tokens
  if (category && categoryConceptsMap && categoryConceptsMap[category] && expandedTokens && expandedTokens.size > 0) {
    const categoryConceptArray = categoryConceptsMap[category];
    for (const concept of categoryConceptArray) {
      if (expandedTokens.has(concept.toLowerCase())) {
        score += 3;
        break; // Only count once per category
      }
    }
  }

  // Emotion-based category boost: +2 if this entry's category is in emotionBoostedCategories
  if (category && emotionBoostedCategories && emotionBoostedCategories.has(category)) {
    score += 2;
  }

  return score;
}

/**
 * Selects relevant lore entries based on message and mood
 * @param {Object} lorebook - Loaded lorebook structure
 * @param {string} userMessage - User's message text
 * @param {string} currentMood - Current mood (e.g., 'hostile', 'calm')
 * @param {number} n - Number of entries to return (default 2)
 * @param {Object} conceptGraph - Concept graph for token expansion (optional, default null)
 * @param {Object} categoryConceptsMap - Category to concepts mapping (optional, default null)
 * @returns {Array<string>} Array of selected lore entries
 */
export function selectLore(lorebook, userMessage, currentMood, n = 2, conceptGraph = null, categoryConceptsMap = null) {
  // Validate inputs
  if (!lorebook || typeof lorebook !== 'object') {
    return [];
  }

  if (!userMessage || typeof userMessage !== 'string') {
    userMessage = '';
  }

  const messageTokens = tokenizeMessage(userMessage);

  // Classify emotions/intents/topics and build boosted category set
  const emotionTokens = classifyMessage(userMessage) || [];
  const emotionBoostedCategories = new Set();
  for (const token of emotionTokens) {
    if (EMOTION_CATEGORY_AFFINITY[token]) {
      for (const category of EMOTION_CATEGORY_AFFINITY[token]) {
        emotionBoostedCategories.add(category);
      }
    }
  }

  // Expand tokens using concept graph if available
  const expandedTokens = conceptGraph ? expandTokens(messageTokens, conceptGraph) : null;

  // Flatten all entries from all categories
  const allEntries = [];
  if (lorebook.categories) {
    for (const [category, entries] of Object.entries(lorebook.categories)) {
      if (Array.isArray(entries)) {
        allEntries.push(
          ...entries.map(entry => ({
            text: entry,
            category,
          }))
        );
      }
    }
  }

  // Score all entries with concept expansion support and emotion boosting
  const scored = allEntries.map(entry => ({
    ...entry,
    score: scoreLoreEntry(entry.text, messageTokens, currentMood, expandedTokens, categoryConceptsMap, entry.category, emotionBoostedCategories),
  }));

  // Separate entries by score for handling ties
  const withScore = scored.filter(e => e.score > 0);
  const noScore = scored.filter(e => e.score === 0);

  // If we have entries with non-zero score, use them
  if (withScore.length > 0) {
    // Sort by score descending
    withScore.sort((a, b) => b.score - a.score);

    // Group by score for tie-breaking via shuffle
    const result = [];
    let currentScore = withScore[0].score;
    let tieGroup = [];

    for (const entry of withScore) {
      if (entry.score !== currentScore && tieGroup.length > 0) {
        // Shuffle the tie group and add n items total
        shuffleArray(tieGroup);
        result.push(...tieGroup);
        if (result.length >= n) break;
        tieGroup = [];
        currentScore = entry.score;
      }
      tieGroup.push(entry);
    }

    // Add remaining tie group
    if (tieGroup.length > 0) {
      shuffleArray(tieGroup);
      result.push(...tieGroup);
    }

    // Return top n
    return result.slice(0, n).map(e => e.text);
  }

  // If nothing scores > 0, return n random entries
  shuffleArray(noScore);
  return noScore.slice(0, n).map(e => e.text);
}

/**
 * Formats selected lore entries for inclusion in the system prompt
 * Handles 0, 1, or 2+ entries gracefully
 * @param {Array<string>} entries - Array of lore entry strings
 * @returns {string} Formatted lore text for prompt injection
 */
export function formatLoreForPrompt(entries) {
  if (!entries || entries.length === 0) {
    return '';
  }

  if (entries.length === 1) {
    return `Packy remembers: ${entries[0]}`;
  }

  // 2 or more entries
  const formattedEntries = entries
    .slice(0, 2) // Only use first 2
    .map((entry, index) => {
      if (index === 0) {
        return `Packy remembers: ${entry}`;
      }
      return `Packy also recalls: ${entry}`;
    });

  return formattedEntries.join('\n');
}

/**
 * Shuffles an array in-place (Fisher-Yates shuffle)
 * @param {Array} arr - Array to shuffle
 */
function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}
