export class PackyState {
  constructor() {
    this.turn = 0;
    this.snark = 0.0;
    this.mood = 'neutral';
    this.cpu = 0.0;
    this.temp = null;
    this.weather = 'unknown';
    this.keywords = [];
  }

  asPromptBlock() {
    const tempStr = this.temp != null ? `${this.temp}°C` : 'N/A';
    return (
      `System status:\n` +
      `- Mood: ${this.mood}\n` +
      `- Snark level: ${this.snark.toFixed(1)} / 5\n` +
      `- CPU load: ${this.cpu.toFixed(0)}%\n` +
      `- Outside temperature: ${tempStr}\n` +
      `- Weather: ${this.weather}\n`
    );
  }
}
