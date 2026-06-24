/**
 * Claude API Adapter
 * Calls Anthropic Claude API for text generation
 * Replaces the old llama.cpp local inference approach
 */

import Anthropic from '@anthropic-ai/sdk';

// Lazy-initialize: dotenv.config() runs in index.js before any API call,
// but ESM module evaluation happens before that — so don't construct at load time.
let _client = null;
function getClient() {
  if (!_client) {
    _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }
  return _client;
}

/**
 * Call Claude API with given system prompt and user text
 * @param {string} systemPrompt - System prompt for context and behavior
 * @param {string} userText - User input text
 * @param {object} options - Configuration options
 * @param {string} options.model - Model ID (default from CLAUDE_MODEL env var or claude-haiku-4-5-20251001)
 * @param {number} options.maxTokens - Max output tokens (default: 800)
 * @param {number} options.temperature - Temperature for sampling (default: 0.8)
 * @returns {Promise<{text: string, inputTokens: number, outputTokens: number}>}
 * @throws {Error} Descriptive errors for rate limits, auth failures, etc.
 */
export async function callClaude(systemPrompt, userText, options = {}) {
  const {
    model = process.env.CLAUDE_MODEL || 'claude-haiku-4-5-20251001',
    maxTokens = 800,
    temperature = 0.8,
  } = options;

  // Validate API key
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error(
      'ANTHROPIC_API_KEY environment variable is not set. ' +
      'Please configure your Anthropic API key.'
    );
  }

  if (!systemPrompt || typeof systemPrompt !== 'string') {
    throw new Error('systemPrompt must be a non-empty string');
  }

  if (!userText || typeof userText !== 'string') {
    throw new Error('userText must be a non-empty string');
  }

  try {
    const response = await getClient().messages.create({
      model,
      max_tokens: maxTokens,
      temperature,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: userText,
        },
      ],
    });

    // Extract text from response
    let text = '';
    if (response.content && Array.isArray(response.content)) {
      for (const block of response.content) {
        if (block.type === 'text') {
          text += block.text;
        }
      }
    }

    return {
      text,
      inputTokens: response.usage.input_tokens,
      outputTokens: response.usage.output_tokens,
    };
  } catch (error) {
    // Handle specific API errors
    if (error.status === 429) {
      throw new Error(
        `Claude API rate limit exceeded. Retry-After: ${error.headers?.['retry-after'] || 'unknown'}. ${error.message}`,
        { cause: error }
      );
    }

    if (error.status === 401) {
      throw new Error(
        'Claude API authentication failed. Please check your ANTHROPIC_API_KEY.',
        { cause: error }
      );
    }

    if (error.status === 403) {
      throw new Error(
        'Claude API access forbidden. Your API key may not have permission for this model.',
        { cause: error }
      );
    }

    if (error.status === 400) {
      throw new Error(`Claude API request error: ${error.message}`, { cause: error });
    }

    if (error.status === 500 || error.status === 502 || error.status === 503) {
      throw new Error(
        `Claude API server error (${error.status}). The service may be temporarily unavailable.`,
        { cause: error }
      );
    }

    // Generic error handling
    throw new Error(
      `Claude API call failed: ${error.message || 'Unknown error'}`,
      { cause: error }
    );
  }
}

/**
 * Call Claude API with exponential backoff retry on rate limit
 * @param {string} systemPrompt - System prompt for context and behavior
 * @param {string} userText - User input text
 * @param {object} options - Configuration options (same as callClaude)
 * @param {number} retries - Number of retry attempts (default: 2)
 * @returns {Promise<{text: string, inputTokens: number, outputTokens: number}>}
 * @throws {Error} After exhausting all retries
 */
export async function callWithRetry(
  systemPrompt,
  userText,
  options = {},
  retries = 2
) {
  let lastError;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await callClaude(systemPrompt, userText, options);
    } catch (error) {
      lastError = error;

      // Only retry on rate limit errors (429)
      if (!error.message.includes('rate limit')) {
        throw error;
      }

      // If this was the last attempt, throw
      if (attempt === retries) {
        throw error;
      }

      // Exponential backoff: 1s, 2s, etc.
      const delayMs = Math.pow(2, attempt) * 1000;
      console.warn(
        `Claude API rate limited. Retrying in ${delayMs}ms (attempt ${attempt + 1}/${retries})`
      );
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  // Should not reach here, but just in case
  throw lastError;
}
