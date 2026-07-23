const COLORS = {
  HOSTILE: 0xff2020,
  SNARKY: 0xff6600,
  IRRITATED: 0xffcc00,
  CALM: 0x00cc66,
  LORE: 0x4a4a8a,
  WAR: 0x8b0000,
  SNARK: 0xff4500,
  STATUS: 0x2f3136,
  CHAOS: 0x9b59b6,
  HELP: 0x3498db,
  ADMIN: 0xe74c3c,
};

function moodColor(mood) {
  const m = (mood || '').toUpperCase();
  if (m === 'HOSTILE' || m === 'FURIOUS') return COLORS.HOSTILE;
  if (m === 'SNARKY' || m === 'GRUMPY') return COLORS.SNARKY;
  if (m === 'IRRITATED') return COLORS.IRRITATED;
  return COLORS.CALM;
}

export { COLORS, moodColor };
