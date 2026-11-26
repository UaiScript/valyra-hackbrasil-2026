import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveDestination, REPOSITORY_URL } from '../config/destination.mjs';

test('default and example destination use the official repository', () => {
  assert.deepEqual(resolveDestination({}), { kind: 'repository', url: REPOSITORY_URL });
  assert.equal(resolveDestination({ VITE_SYSTEM_URL: REPOSITORY_URL }).url, REPOSITORY_URL);
});
test('future application destination is an explicit build-time decision', () => {
  assert.deepEqual(resolveDestination({ VITE_DESTINATION_KIND: 'application', VITE_SYSTEM_URL: 'https://app.example.com' }),
    { kind: 'application', url: 'https://app.example.com/' });
  assert.throws(() => resolveDestination({ VITE_DESTINATION_KIND: 'application' }));
  assert.throws(() => resolveDestination({ VITE_DESTINATION_KIND: 'application', VITE_SYSTEM_URL: REPOSITORY_URL }));
});
for (const url of ['javascript:alert(1)', 'data:text/html,test', '//example.com', '/app', 'http://example.com', 'https://user:secret@example.com', 'https://evil.example']) {
  test(`reject unsafe or unofficial repository destination: ${url.split(':')[0]}`, () => {
    assert.throws(() => resolveDestination({ VITE_SYSTEM_URL: url }));
  });
}
test('application also rejects executable schemes and embedded credentials', () => {
  for (const url of ['javascript:alert(1)', 'https://user:secret@example.com', 'http://example.com']) {
    assert.throws(() => resolveDestination({ VITE_SYSTEM_URL: url, VITE_DESTINATION_KIND: 'application' }));
  }
  assert.throws(() => resolveDestination({ VITE_DESTINATION_KIND: 'unknown' }));
});

import { resolveApi, DEFAULT_PROXY_TARGET } from '../config/api.mjs';

test('api defaults to same origin behind the Vite proxy', () => {
  assert.deepEqual(resolveApi({}), { proxyTarget: DEFAULT_PROXY_TARGET, apiOrigin: null, connectSrc: "'self'" });
});
test('explicit api origin is added to the CSP', () => {
  const api = resolveApi({ VITE_API_URL: 'https://api.example.com' });
  assert.equal(api.apiOrigin, 'https://api.example.com');
  assert.equal(api.connectSrc, "'self' https://api.example.com");
  assert.equal(resolveApi({ VITE_API_URL: 'http://localhost:8000' }).apiOrigin, 'http://localhost:8000');
});
for (const url of ['javascript:alert(1)', 'http://api.example.com', 'https://user:secret@api.example.com', 'https://api.example.com/v1', '/api']) {
  test(`reject unsafe api url: ${url.split(':')[0]}`, () => {
    assert.throws(() => resolveApi({ VITE_API_URL: url }));
  });
}
