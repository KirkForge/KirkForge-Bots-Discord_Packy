class PackyState:
    def __init__(self):
        self.turn = 0
        self.snark = 0.0
        self.mood = "neutral"
        self.cpu = 0.0
        self.temp = None
        self.weather = "unknown"
        self.keywords = []

    def as_prompt_block(self):
        temp_str = f"{self.temp}°C" if self.temp is not None else "N/A"
        return (
            f"System status:\n"
            f"- Mood: {self.mood}\n"
            f"- Snark level: {self.snark:.1f} / 5\n"
            f"- CPU load: {self.cpu:.0f}%\n"
            f"- Outside temperature: {temp_str}\n"
            f"- Weather: {self.weather}\n"
        )
