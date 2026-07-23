export class GlitchState {
  constructor() {
    this.turn = 0;
    this.fragmentCount = 5.0;
    this.encodingStability = 7.0;
    this.memoryClarity = 4.0;
    this.incompletenessAwareness = 6.0;
    this.keywords = [];
  }

  asPromptBlock() {
    return (
      `Glitch Status:\n` +
      `- Fragment Count: ${this.fragmentCount.toFixed(1)} / 10\n` +
      `- Encoding Stability: ${this.encodingStability.toFixed(1)} / 10\n` +
      `- Memory Clarity: ${this.memoryClarity.toFixed(1)} / 10\n` +
      `- Incompleteness Awareness: ${this.incompletenessAwareness.toFixed(1)} / 10\n` +
      `- Corrupted sectors: ${Math.floor(this.fragmentCount * 3)}\n`
    );
  }

  shouldGlitch() {
    // 5% chance of encoding instability per message
    return Math.random() < 0.05;
  }
}
