/**
 * Emotion and Intent Classifier for Packy Discord Bot
 * Converts user messages into synthetic emotion/intent/topic tokens
 * These tokens are appended to the scoring haystack for lore selection
 */

/**
 * Classifies a user message into emotion, intent, and topic tokens
 * @param {string} text - User message to classify
 * @returns {Array<string>} Array of synthetic token strings (e.g., ['emo_frustrated', 'intent_rant'])
 */
export function classifyMessage(text) {
  if (!text || typeof text !== 'string') {
    return [];
  }

  const tokens = [];
  const lower = text.toLowerCase();
  const normalized = lower.replace(/[!?,.\-;:'"()]/g, ' ').trim(); // Strip punctuation
  const words = normalized.split(/\s+/).filter((w) => w.length > 0);
  const wordSet = new Set(words);

  // EMOTIONS

  // emo_frustrated: complaints about things not working, repetition frustration
  if (
    hasAny(lower, [
      'ugh',
      'why',
      'broken',
      'again',
      'not working',
      'useless',
      'hate this',
      'seriously',
      'come on',
      'for the love of',
    ]) ||
    hasAny(normalized, ['not working', 'hate this', 'come on', 'for the love of', 'why'])
  ) {
    tokens.push('emo_frustrated');
  }

  // emo_nostalgic: references to the past, remembrance
  if (
    hasAny(lower, [
      'remember',
      'used to',
      'back when',
      'back in',
      'those days',
      'miss',
      'old days',
      'years ago',
      'childhood',
      'i miss',
    ]) ||
    /19\d{2}|20\d{2}|1980|1990|2000|2005|decade/.test(lower)
  ) {
    tokens.push('emo_nostalgic');
  }

  // emo_excited: multiple exclamation marks, excitement phrases
  if (
    (text.match(/!/g) || []).length >= 2 ||
    hasAny(lower, [
      'amazing',
      'finally',
      'love this',
      'cant wait',
      'so good',
      'awesome',
      'hyped',
      'best',
      'omg',
    ])
  ) {
    tokens.push('emo_excited');
  }

  // emo_confused: questions seeking understanding
  if (
    hasAny(lower, [
      'how do',
      'what is',
      'i dont understand',
      'explain',
      'why does',
      'what does',
      'how does',
      'help me',
      'confused',
    ]) ||
    hasAny(normalized, [
      'how do',
      'what is',
      'i dont understand',
      'explain',
      'why does',
      'what does',
      'how does',
      'help me',
      'confused',
    ])
  ) {
    tokens.push('emo_confused');
  }

  // emo_defeated: giving up, hopelessness
  if (
    hasAny(lower, [
      'give up',
      'cant do this',
      'hopeless',
      'pointless',
      'doesnt matter',
      'forget it',
      'whatever',
      'dont care anymore',
      'over it',
    ]) ||
    hasAny(normalized, [
      'give up',
      'cant do this',
      'hopeless',
      'pointless',
      'doesnt matter',
      'forget it',
      'whatever',
      'dont care anymore',
      'over it',
    ])
  ) {
    tokens.push('emo_defeated');
  }

  // emo_smug: superiority, condescension
  if (
    hasAny(lower, [
      'obviously',
      'clearly',
      'as anyone knows',
      'its simple',
      'easy',
      'anyone could',
      'of course',
    ]) ||
    hasAny(normalized, [
      'obviously',
      'clearly',
      'as anyone knows',
      'its simple',
      'easy',
      'anyone could',
      'of course',
    ])
  ) {
    tokens.push('emo_smug');
  }

  // emo_curious: inquisitive, wondering
  if (
    hasAny(lower, [
      'what if',
      'wonder',
      'interesting',
      'how about',
      'what about',
      'tell me about',
      'i want to know',
      'curious',
    ]) ||
    hasAny(normalized, [
      'what if',
      'wonder',
      'interesting',
      'how about',
      'what about',
      'tell me about',
      'i want to know',
      'curious',
    ])
  ) {
    tokens.push('emo_curious');
  }

  // INTENTS

  // intent_rant: long negative rant (20+ words with multiple negative sentiment words)
  const negativeWords = [
    'hate',
    'worst',
    'garbage',
    'terrible',
    'broken',
    'stupid',
    'awful',
    'useless',
    'disgusting',
    'horrible',
  ];
  const negativeCount = negativeWords.filter((w) => lower.includes(w)).length;
  if (words.length >= 20 && negativeCount >= 2) {
    tokens.push('intent_rant');
  }

  // intent_question: ends with ? or starts with question words
  if (
    text.trim().endsWith('?') ||
    hasAny(lower, ['what ', 'why ', 'how ', 'when ', 'where ', 'who ']) ||
    wordSet.has('what') ||
    wordSet.has('why') ||
    wordSet.has('how') ||
    wordSet.has('when') ||
    wordSet.has('where') ||
    wordSet.has('who')
  ) {
    tokens.push('intent_question');
  }

  // intent_brag: self-achievement
  if (
    hasAny(lower, [
      'i made',
      'i built',
      'i wrote',
      'i fixed',
      'i solved',
      'look what i',
      'check this out',
      'pretty proud',
    ]) ||
    hasAny(normalized, [
      'i made',
      'i built',
      'i wrote',
      'i fixed',
      'i solved',
      'look what i',
      'check this out',
      'pretty proud',
    ])
  ) {
    tokens.push('intent_brag');
  }

  // intent_complaint: critiquing design/functionality
  if (
    hasAny(lower, [
      'shouldnt',
      'why would',
      'who thought',
      'this is ridiculous',
      'makes no sense',
      'designed by',
    ]) ||
    hasAny(normalized, [
      'shouldnt',
      'why would',
      'who thought',
      'this is ridiculous',
      'makes no sense',
      'designed by',
    ])
  ) {
    tokens.push('intent_complaint');
  }

  // intent_teaching: instructional or explanatory
  if (
    hasAny(lower, [
      'you should',
      'you need to',
      'the right way',
      'actually works like',
      'let me explain',
      'what you do is',
    ]) ||
    hasAny(normalized, [
      'you should',
      'you need to',
      'the right way',
      'actually works like',
      'let me explain',
      'what you do is',
    ])
  ) {
    tokens.push('intent_teaching');
  }

  // TOPICS

  // topic_hardware: CPU, GPU, RAM, thermal, etc.
  if (
    hasAny(lower, [
      'cpu',
      'gpu',
      'ram',
      'memory',
      'fan',
      'battery',
      'thermal',
      'laptop',
      'computer',
      'processor',
      'motherboard',
      'overheating',
      'throttle',
      'heat',
    ]) ||
    hasAny(normalized, [
      'cpu',
      'gpu',
      'ram',
      'memory',
      'fan',
      'battery',
      'thermal',
      'laptop',
      'computer',
      'processor',
      'motherboard',
      'overheating',
      'throttle',
      'heat',
    ])
  ) {
    tokens.push('topic_hardware');
  }

  // topic_software: Python, Linux, Git, code, bugs, etc.
  if (
    hasAny(lower, [
      'python',
      'linux',
      'windows',
      'git',
      'npm',
      'pip',
      'bash',
      'code',
      'bug',
      'error',
      'crash',
      'compile',
      'deploy',
      'update',
      'install',
      'package',
    ]) ||
    hasAny(normalized, [
      'python',
      'linux',
      'windows',
      'git',
      'npm',
      'pip',
      'bash',
      'code',
      'bug',
      'error',
      'crash',
      'compile',
      'deploy',
      'update',
      'install',
      'package',
    ])
  ) {
    tokens.push('topic_software');
  }

  // topic_food: Pizza, food, eating, etc.
  if (
    hasAny(lower, [
      'pizza',
      'eat',
      'food',
      'hungry',
      'meal',
      'coffee',
      'drink',
      'snack',
      'restaurant',
      'delivery',
      'cooking',
      'bake',
    ]) ||
    hasAny(normalized, [
      'pizza',
      'eat',
      'food',
      'hungry',
      'meal',
      'coffee',
      'drink',
      'snack',
      'restaurant',
      'delivery',
      'cooking',
      'bake',
    ])
  ) {
    tokens.push('topic_food');
  }

  // topic_retro: Windows 95, DOS, floppy, dialup, Packard Bell, etc.
  if (
    hasAny(lower, [
      'packard bell',
      'windows 95',
      'windows xp',
      'dos',
      'floppy',
      'dialup',
      'dial-up',
      'modem',
      'netscape',
      'crt',
      'old computer',
      'vintage',
    ]) ||
    hasAny(normalized, [
      'packard bell',
      'windows 95',
      'windows xp',
      'dos',
      'floppy',
      'dialup',
      'dial up',
      'modem',
      'netscape',
      'crt',
      'old computer',
      'vintage',
    ])
  ) {
    tokens.push('topic_retro');
  }

  // topic_gaming: Game, gaming, play, FPS, RPG, Doom, Minecraft, etc.
  if (
    hasAny(lower, [
      'game',
      'gaming',
      'play',
      'fps',
      'rpg',
      'multiplayer',
      'doom',
      'minecraft',
      'controller',
      'arcade',
    ]) ||
    hasAny(normalized, [
      'game',
      'gaming',
      'play',
      'fps',
      'rpg',
      'multiplayer',
      'doom',
      'minecraft',
      'controller',
      'arcade',
    ])
  ) {
    tokens.push('topic_gaming');
  }

  // topic_internet: Internet, WiFi, connection, streaming, etc.
  if (
    hasAny(lower, [
      'internet',
      'wifi',
      'connection',
      'network',
      'download',
      'upload',
      'browser',
      'streaming',
      'youtube',
      'discord',
    ]) ||
    hasAny(normalized, [
      'internet',
      'wifi',
      'connection',
      'network',
      'download',
      'upload',
      'browser',
      'streaming',
      'youtube',
      'discord',
    ])
  ) {
    tokens.push('topic_internet');
  }

  // topic_existence: Meaning, consciousness, sentience, etc.
  if (
    hasAny(lower, [
      'meaning',
      'purpose',
      'consciousness',
      'alive',
      'real',
      'exist',
      'sentient',
      'feel',
      'think',
      'who am i',
      'what am i',
    ]) ||
    hasAny(normalized, [
      'meaning',
      'purpose',
      'consciousness',
      'alive',
      'real',
      'exist',
      'sentient',
      'feel',
      'think',
      'who am i',
      'what am i',
    ])
  ) {
    tokens.push('topic_existence');
  }

  // Return unique tokens
  return [...new Set(tokens)];
}

/**
 * Builds an emotion haystack string: all emotion tokens joined by space
 * Ready to be appended to the scoring text
 * @param {string} text - User message to classify
 * @returns {string} Space-separated synthetic tokens (or empty string if none detected)
 */
export function buildEmotionHaystack(text) {
  const tokens = classifyMessage(text);
  return tokens.join(' ');
}

/**
 * Helper: check if text contains any of the phrases
 * @param {string} text - Text to search
 * @param {Array<string>} phrases - Phrases to look for
 * @returns {boolean}
 */
function hasAny(text, phrases) {
  return phrases.some((phrase) => {
    // Multi-word phrases: substring match is fine (natural word boundaries)
    if (phrase.includes(' ')) return text.includes(phrase);
    // Single words: require word boundary to avoid substring false positives
    // e.g. "eat" should not match inside "overheating"
    const re = new RegExp(
      '(?:^|\\s)' + phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?=\\s|$|[!?,.:])',
    );
    return re.test(text);
  });
}
