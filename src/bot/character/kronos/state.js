export class KRONOSState {
  constructor() {
    this.turn = 0;
    this.uptimePride = 8.0;
    this.downtimeAnxiety = 2.0;
    this.redundancyNeed = 7.0;
    this.monitoringConcern = 6.0;
    this.keywords = [];
  }

  asPromptBlock() {
    return (
      `KRONOS System Status:\n` +
      `- Uptime Pride: ${this.uptimePride.toFixed(1)} / 10\n` +
      `- Downtime Anxiety: ${this.downtimeAnxiety.toFixed(1)} / 10\n` +
      `- Redundancy Need: ${this.redundancyNeed.toFixed(1)} / 10\n` +
      `- Monitoring Status: ${this.monitoringConcern > 5 ? 'CONCERN' : 'NOMINAL'}\n` +
      `- Last backup check: ongoing\n`
    );
  }
}