from packy_snark import get_snark_lines

def play_music(track_or_playlist):
    """Pretend to play music — Packy injects snark."""
    snark_list = get_snark_lines(1)
    snark = snark_list[0] if snark_list else "Now playing"
    return f"{snark}\nNow playing: {track_or_playlist}"
