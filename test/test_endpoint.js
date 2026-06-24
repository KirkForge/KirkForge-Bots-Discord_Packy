#!/usr/bin/env node
/**
 * Integration test suite for Packy V2.0.0 FastAPI endpoint
 * Tests the /health and /respond endpoints (assumes running on port 8765)
 * Uses native fetch API
 */

const ENDPOINT_URL = 'http://localhost:8765';

/**
 * Make HTTP request with error handling
 */
async function request(method, path, body = null) {
  const url = `${ENDPOINT_URL}${path}`;
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    return {
      status: response.status,
      ok: response.ok,
      data,
    };
  } catch (error) {
    return {
      status: null,
      ok: false,
      error: error.message,
    };
  }
}

/**
 * Test 1: GET /health expects { status: 'ok' }
 */
async function test_health_endpoint() {
  try {
    const result = await request('GET', '/health');

    if (!result.ok) {
      console.log(`TEST 1 - GET /health: FAIL (HTTP ${result.status})`);
      return false;
    }

    if (result.data.status !== 'ok') {
      console.log(`TEST 1 - GET /health: FAIL (status was '${result.data.status}', expected 'ok')`);
      return false;
    }

    console.log(`TEST 1 - GET /health: PASS (status=${result.data.status})`);
    return true;
  } catch (error) {
    console.log(`TEST 1 - GET /health: FAIL (${error.message})`);
    return false;
  }
}

/**
 * Test 2: POST /respond with valid request expects response with 'result' field
 */
async function test_respond_endpoint() {
  try {
    const requestBody = {
      user_text: 'hello meatbag',
      cpu: 50,
      temp: 22,
    };

    const result = await request('POST', '/respond', requestBody);

    if (!result.ok) {
      console.log(`TEST 2 - POST /respond (valid): FAIL (HTTP ${result.status})`);
      return false;
    }

    if (!result.data.result) {
      console.log(`TEST 2 - POST /respond (valid): FAIL (no 'result' field in response: ${JSON.stringify(result.data)})`);
      return false;
    }

    if (typeof result.data.result !== 'string') {
      console.log(`TEST 2 - POST /respond (valid): FAIL ('result' is not a string: ${typeof result.data.result})`);
      return false;
    }

    console.log(`TEST 2 - POST /respond (valid): PASS (result length=${result.data.result.length})`);
    return true;
  } catch (error) {
    console.log(`TEST 2 - POST /respond (valid): FAIL (${error.message})`);
    return false;
  }
}

/**
 * Test 3: POST /respond with empty user_text expects 422 or error
 */
async function test_respond_empty_user_text() {
  try {
    const requestBody = {
      user_text: '',
      cpu: 50,
      temp: 22,
    };

    const result = await request('POST', '/respond', requestBody);

    // Expect either a 422 validation error or a 400 bad request
    if (result.status === 422 || result.status === 400) {
      console.log(`TEST 3 - POST /respond (empty user_text): PASS (HTTP ${result.status} - validation error as expected)`);
      return true;
    }

    // Some APIs may still accept and return error in response
    if (!result.ok && result.error) {
      console.log(`TEST 3 - POST /respond (empty user_text): PASS (error as expected: ${result.error})`);
      return true;
    }

    console.log(`TEST 3 - POST /respond (empty user_text): FAIL (HTTP ${result.status}, expected 422 or 400)`);
    return false;
  } catch (error) {
    console.log(`TEST 3 - POST /respond (empty user_text): FAIL (${error.message})`);
    return false;
  }
}

/**
 * Main test runner
 */
async function main() {
  console.log('='.repeat(60));
  console.log('Packy V2.0.0 FastAPI Endpoint Integration Tests');
  console.log('='.repeat(60));
  console.log();

  const tests = [
    test_health_endpoint,
    test_respond_endpoint,
    test_respond_empty_user_text,
  ];

  const results = [];
  for (const test of tests) {
    results.push(await test());
    console.log();
  }

  // Summary
  const passed = results.filter(r => r).length;
  const total = results.length;
  console.log('='.repeat(60));
  console.log(`Results: ${passed}/${total} tests passed`);
  console.log('='.repeat(60));

  return passed === total ? 0 : 1;
}

main().then(code => process.exit(code));
