export class VernonState {
  constructor() {
    this.turn = 0;
    this.patienceLevel = 7.0;
    this.domainEnergy = 5.0;
    this.nostalgia = 3.0;
    this.keywords = [];
  }

  asPromptBlock() {
    return (
      `Vernon Status:\n` +
      `- Patience: ${this.patienceLevel.toFixed(1)} / 10\n` +
      `- Domain Energy: ${this.domainEnergy.toFixed(1)} / 10\n` +
      `- Nostalgia: ${this.nostalgia.toFixed(1)} / 10\n` +
      `- Owned domains: checking occasionally\n`
    );
  }
}
