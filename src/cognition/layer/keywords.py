
KEYWORDS = {
    "angry": ["hate", "angry", "mad", "furious"],
    "happy": ["love", "great", "nice", "awesome"],
    "technical": ["cpu", "temperature", "system", "load"],
}

def extract_keywords(text):
    found = []
    lower = text.lower()
    for k, words in KEYWORDS.items():
        if any(w in lower for w in words):
            found.append(k)
    return found
