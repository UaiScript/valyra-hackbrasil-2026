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
