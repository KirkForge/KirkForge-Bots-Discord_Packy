// @ts-nocheck — TODO: add types
import os from 'os';
import { logger } from './logger.js';

/**
 * Read current CPU load as percentage (0-100)
 * Uses os.loadavg()[0] (1-min average) normalized by CPU count
 * @returns {number} CPU percentage clamped to 0-100
 */
export function readCpu() {
  const loadAvg = os.loadavg()[0];
  const cpuCount = os.cpus().length;
  const cpuPercent = (loadAvg / cpuCount) * 100;
  return Math.min(Math.max(cpuPercent, 0), 100);
}

/**
 * Read weather from OpenWeatherMap API
 * @param {string|null} apiKey - OpenWeatherMap API key
 * @param {string} location - City name or location string
 * @returns {Promise<{temp: number|null, description: string}>} Weather data
 */
export async function readWeather(apiKey, location) {
  if (!apiKey) {
    return { temp: null, description: 'unknown' };
  }

  try {
    const url = new URL('https://api.openweathermap.org/data/2.5/weather');
    url.searchParams.set('q', location || 'London'); // Default to London if no location
    url.searchParams.set('appid', apiKey);
    url.searchParams.set('units', 'metric');

    // Use AbortController for timeout if supported (Node.js 15+)
    let controller;
    let timeoutId;
    const options = {};

    try {
      controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 5000);
      options.signal = controller.signal;
    } catch {
      /* non-fatal: no AbortController support */
    }

    const response = await fetch(url.toString(), options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      logger.warn('Weather API error', { status: response.status });
      return { temp: null, description: 'unknown' };
    }

    const data = await response.json();
    return {
      temp: data.main?.temp ?? null,
      description: data.weather?.[0]?.description ?? 'unknown',
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      logger.warn('Weather API request timed out');
    } else {
      logger.warn('Weather API error', { error: error.message });
    }
    return { temp: null, description: 'unknown' };
  }
}

/**
 * Read both CPU and weather signals at once
 * @param {string|null} apiKey - OpenWeatherMap API key
 * @param {string} location - City name or location string
 * @returns {Promise<{cpu: number, temp: number|null, weather: string}>} Combined signals
 */
export async function readSignals(apiKey, location) {
  const cpu = readCpu();
  const { temp, description } = await readWeather(apiKey, location);
  return {
    cpu,
    temp,
    weather: description,
  };
}
