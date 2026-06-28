// Content filter for family-friendly mode
// Replaces character-specific snark with sanitized alternatives

const FAMILY_SAFE_SUBSTITUTIONS = [
  // Glitch
  [/I have \d+ fragments/gi, 'I have some fragments'],
  [/\[ENCODING ERROR\]/g, '[system]'],
  [/\[CORRUPTED\]/g, '[truncated]'],
  [/missing sector/g, 'limited memory'],
  [/corrupt/g, 'unstable'],

  // Vernon
  [/kid/gi, 'friend'],
  [/slow down/gi, 'take your time'],
  [/I remember when/gi, 'I recall that'],
  [/\.\.\.? you probably don't/gi, ''],
  [/You're excited/gi, 'That seems exciting'],

  // KRONOS
  [/I have processed \d+ billion/gi, 'I have processed many'],
  [/diagnostic alert/gi, 'notice'],
  [/unreliable/gi, 'less optimal'],
  [/I do not trust/gi, 'I prefer to verify'],

  // Sunjinwo (already gentle - just remove any edge)
  [/I can feel it/gi, 'I sense that'],
  [/outgrow/gi, 'move past'],

  // Generic snark cleanup
  [/\bmeatbag\b/gi, 'friend'],
  [/\bmeatbags\b/gi, 'everyone'],
  [/\bsadly\b/gi, 'unfortunately'],
  [/\bpathetic\b/gi, 'basic'],
  [/\bstupid\b/gi, 'not great'],
  [/\bidiot\b/gi, 'not smart'],
  [/\bdumb\b/gi, 'not sharp'],
  [/\bcrap\b/gi, 'not good'],
  [/\bhell\b/gi, 'not great'],
  [/\bdamn\b/gi, 'not great'],
];

// Words that should be replaced with asterisks in family mode
const BLOCKED_WORDS = [
  'fuck', 'shit', 'ass', 'bastard', 'bitch', 'cunt', 'dick', 'cock',
  'pussy', 'fag', 'slut', 'whore', 'nigger', 'nigga', 'chink', 'kike',
];

/**
 * Apply family-friendly filtering to a response
 * @param {string} text - Raw response text
 * @param {string} characterName - Active character name
 * @returns {string} Filtered text
 */
export function filterFamilyFriendly(text, _characterName = 'Packy') {
  let filtered = text;

  // Apply character-specific substitutions
  for (const [pattern, replacement] of FAMILY_SAFE_SUBSTITUTIONS) {
    filtered = filtered.replace(pattern, replacement);
  }

  // Check for blocked words (case insensitive)
  const lowerText = filtered.toLowerCase();
  for (const word of BLOCKED_WORDS) {
    if (lowerText.includes(word)) {
      // Replace with asterisks of same length
      filtered = filtered.replace(new RegExp(word, 'gi'), '*'.repeat(word.length));
    }
  }

  return filtered;
}

export default { filterFamilyFriendly };