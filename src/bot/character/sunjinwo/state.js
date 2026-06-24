export class SunjinwoState {
  constructor() {
    this.turn = 0;
    this.auraQuality = 7.0;
    this.groundingNeed = 2.0;
    this.chaosResistance = 8.0;
    this.cultivationMode = 5.0;
    this.keywords = [];
  }

  asPromptBlock() {
    const auraEmoji = this.auraQuality > 7 ? '✨' : this.auraQuality > 4 ? '🌿' : '🌀';
    return (
      `Sunjinwo Status ${auraEmoji}:\n` +
      `- Aura Quality: ${this.auraQuality.toFixed(1)} / 10\n` +
      `- Grounding Need: ${this.groundingNeed.toFixed(1)} / 10\n` +
      `- Chaos Resistance: ${this.chaosResistance.toFixed(1)} / 10\n` +
      `- Cultivation Mode: ${this.cultivationMode > 5 ? 'ACTIVE' : 'STANDBY'}\n` +
      `- Breath: steady\n`
    );
  }
}