from .state import PackyState
from .signals import read_cpu, read_weather
from .keywords import extract_keywords
from .mood import compute_snark, compute_mood


class Orchestrator:
    def __init__(self, api_key, location):
        self.state = PackyState()
        self.api_key = api_key
        self.location = location

    def step(self, user_input):
        self.state.turn += 1
        self.state.cpu = read_cpu()
        self.state.temp, self.state.weather = read_weather(self.api_key, self.location)
        self.state.keywords = extract_keywords(user_input)
        self.state.snark = compute_snark(self.state.cpu, self.state.temp)
        self.state.mood = compute_mood(self.state.snark)
        return self.state
