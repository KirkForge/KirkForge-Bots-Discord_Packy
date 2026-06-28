/**
 * MiniMax API Adapter
 * Calls MiniMax chat completion API for text generation
 * Alternative provider with same interface as Claude adapter
 */

import { logger } from '../logger.js';

const MINIMAX_API_ENDPOINT = 'https://api.minimaxi.chat/v1/text/chatcompletion_v2';

/**
 * Call MiniMax API with given system prompt and user text
 * @param {string} systemPrompt - System prompt for context and behavior
 * @param {string} userText - User input text
 * @param {object} options - Configuration options
 * @param {string} options.model - Model ID (default from MINIMAX_MODEL env var or MiniMax-Text-01)
 * @param {number} options.maxTokens - Max output tokens (default: 800)
 * @param {number} options.temperature - Temperature for sampling (default: 0.8)
 * @returns {Promise<{text: string, inputTokens: number, outputTokens: number}>}
 * @throws {Error} Descriptive errors for rate limits, auth failures, etc.
 */
export async function callMiniMax(systemPrompt, userText, options = {}) {
  const {
    model = process.env.MINIMAX_MODEL || 'MiniMax-Text-01',
    maxTokens = 800,
    temperature = 0.8,
  } = options;

  // Validate required environment variables
  if (!process.env.MINIMAX_API_KEY) {
    throw new Error(
      'MINIMAX_API_KEY environment variable is not set. ' +
      'Please configure your MiniMax API key.'
    );
  }

  if (!process.env.MINIMAX_GROUP_ID) {
    throw new Error(
      'MINIMAX_GROUP_ID environment variable is not set. ' +
      'Please configure your MiniMax Group ID.'
    );
  }

  if (!systemPrompt || typeof systemPrompt !== 'string') {
    throw new Error('systemPrompt must be a non-empty string');
  }

  if (!userText || typeof userText !== 'string') {
    throw new Error('userText must be a non-empty string');
  }

  try {
    const requestBody = {
      model,
      group_id: process.env.MINIMAX_GROUP_ID,
      messages: [
        {
          sender_type: 'USER',
          sender_name: 'User',
          text: userText,
        },
      ],
      system_prompt: systemPrompt,
      max_tokens: maxTokens,
      temperature,
    };

    const response = await fetch(MINIMAX_API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.MINIMAX_API_KEY}`,
      },
      body: JSON.stringify(requestBody),
    });

    // Handle HTTP errors
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      let errorDetails = '';

      if (contentType?.includes('application/json')) {
        try {
          const errorBody = await response.json();
          errorDetails = JSON.stringify(errorBody);
        } catch { /* non-fatal: fallback to text */ 
          errorDetails = await response.text();
        }
      } else {
        errorDetails = await response.text();
      }

      if (response.status === 429) {
        throw new Error(
          `MiniMax API rate limit exceeded. ${errorDetails || response.statusText}`
        );
      }

      if (response.status === 401) {
        throw new Error(
          'MiniMax API authentication failed. Please check your MINIMAX_API_KEY.'
        );
      }

      if (response.status === 403) {
        throw new Error(
          'MiniMax API access forbidden. Your Group ID or API key may not have permission.'
        );
      }

      if (response.status === 400) {
        throw new Error(`MiniMax API request error: ${errorDetails || response.statusText}`);
      }

      if (response.status >= 500) {
        throw new Error(
          `MiniMax API server error (${response.status}). The service may be temporarily unavailable.`
        );
      }

      throw new Error(
        `MiniMax API call failed with status ${response.status}: ${errorDetails || response.statusText}`
      );
    }

    const data = await response.json();

    // Extract text from response
    let text = '';
    if (data.reply) {
      text = data.reply;
    } else if (data.text) {
      text = data.text;
    } else if (data.choices && Array.isArray(data.choices) && data.choices.length > 0) {
      text = data.choices[0].text || data.choices[0].content || '';
    }

    // Extract token usage (MiniMax response format may vary)
    const inputTokens = data.input_tokens || data.usage?.prompt_tokens || 0;
    const outputTokens = data.output_tokens || data.usage?.completion_tokens || 0;

    return {
      text,
      inputTokens,
      outputTokens,
    };
  } catch (error) {
    // Re-throw known errors
    if (error.message.includes('MiniMax API')) {
      throw error;
    }

    // Handle fetch errors
    throw new Error(
      `MiniMax API call failed: ${error.message || 'Unknown error'}`,
      { cause: error }
    );
  }
}

/**
 * Call MiniMax API with exponential backoff retry on rate limit
 * @param {string} systemPrompt - System prompt for context and behavior
 * @param {string} userText - User input text
 * @param {object} options - Configuration options (same as callMiniMax)
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
      return await callMiniMax(systemPrompt, userText, options);
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
      logger.warn('MiniMax API rate limited, retrying', { delayMs, attempt: attempt + 1, retries });
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  // Should not reach here, but just in case
  throw lastError;
}
