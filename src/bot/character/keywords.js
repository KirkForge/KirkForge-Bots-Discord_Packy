export const KEYWORDS = {
  angry: ['hate', 'angry', 'mad', 'furious'],
  happy: ['love', 'great', 'nice', 'awesome'],
  technical: ['cpu', 'temperature', 'system', 'load'],
};

export function extractKeywords(text) {
  const found = [];
  const lower = text.toLowerCase();

  for (const [k, words] of Object.entries(KEYWORDS)) {
    if (words.some(w => lower.includes(w))) {
      found.push(k);
    }
  }

  return found;
}
