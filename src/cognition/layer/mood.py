
def compute_snark(cpu, temp):
    snark = 0.0
    if cpu is not None:
        snark += (cpu / 100) * 3
    if temp is not None and temp >= 30:
        snark += min((temp - 30) / 10 * 2, 2)
    return min(snark, 5.0)

def compute_mood(snark):
    if snark < 1.0:
        return "calm"
    elif snark < 2.0:
        return "grumpy"
    elif snark < 3.0:
        return "irritated"
    elif snark < 4.0:
        return "snarky"
    elif snark < 4.7:
        return "hostile"
    else:
        return "furious"
