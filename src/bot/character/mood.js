export function computeSnark(cpu, temp) {
  let snark = 0.0;

  if (cpu !== null && cpu !== undefined) {
    snark += (cpu / 100) * 3;
  }

  if (temp !== null && temp !== undefined && temp >= 30) {
    snark += Math.min(((temp - 30) / 10) * 2, 2);
  }

  return Math.min(snark, 5.0);
}

export function computeMood(snark) {
  if (snark < 1.0) {
    return 'calm';
  } else if (snark < 2.0) {
    return 'grumpy';
  } else if (snark < 3.0) {
    return 'irritated';
  } else if (snark < 4.0) {
    return 'snarky';
  } else if (snark < 4.7) {
    return 'hostile';
  } else {
    return 'furious';
  }
}
