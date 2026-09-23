// Local regression tests: no network, paid synthesis, or test accounts created.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

function loadSource(relative) {
  const filename = path.resolve(__dirname, relative);
  const mod = new Module(filename, module);
  mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, filename);
  return mod.exports;
}
const { ChunkedSpeaker } = loadSource('../src/voice/tts.ts');
const { createBrowserTtsPlayer } = loadSource('../src/voice/browserPlayer.ts');
const settle = () => new Promise(resolve => setImmediate(resolve));

function setup(t, play) {
  const log = { requests: 0, cleanup: 0, removed: 0, blocked: 0, errors: [], speaking: [] };
  t.mock.method(globalThis, 'fetch', async () => {
    log.requests++;
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) };
  });
  const player = { play, remove: () => log.removed++, onFinish: cb => { log.finish = cb; } };
  const speaker = new ChunkedSpeaker({
    apiBase: 'https://test.invalid', token: 'unit-only', language: 'en',
    writeAudio: async () => ({ uri: 'test-audio', cleanup: () => log.cleanup++ }),
    createPlayer: () => player,
    onPlaybackBlocked: () => log.blocked++,
    onSpeakingChange: value => log.speaking.push(value),
    onError: message => log.errors.push(message),
  });
  t.after(() => speaker.stop());
  return { speaker, log };
}

test('Safari denial is handled; a direct retry reuses the prepared clip', async t => {
  let denied = true;
  const { speaker, log } = setup(t, () => denied
    ? Promise.reject(new DOMException('Not allowed', 'NotAllowedError')) : Promise.resolve());
  speaker.end('Hello.');
  await settle();
  assert.equal(speaker.playbackBlocked, true);
  assert.equal(log.blocked, 1);
  assert.deepEqual(log.errors, []);
  assert.equal(log.cleanup, 0);
  denied = false;
  speaker.retryPlayback();
  await settle();
  assert.equal(speaker.playbackBlocked, false);
  assert.equal(log.requests, 1);
  assert.deepEqual(log.speaking, [true]);
  log.finish();
  assert.equal(log.cleanup, 1);
  assert.equal(log.removed, 1);
  assert.equal(log.speaking.at(-1), false);
});

test('stop during pending play safely handles the late AbortError', async t => {
  let rejectPlay;
  const { speaker, log } = setup(t, () => new Promise((_, reject) => { rejectPlay = reject; }));
  speaker.end('Hello.');
  await settle();
  speaker.stop();
  rejectPlay(new DOMException('Playback interrupted', 'AbortError'));
  await settle();
  assert.equal(log.cleanup, 1);
  assert.equal(log.removed, 1);
  assert.deepEqual(log.errors, []);
  assert.deepEqual(log.speaking, [false]);
});

test('non-permission playback errors stop and release audio with feedback', async t => {
  const { speaker, log } = setup(t, () => Promise.reject(new Error('Decode failed')));
  speaker.end('Hello.');
  await settle();
  assert.deepEqual(log.errors, ['Decode failed']);
  assert.equal(log.cleanup, 1);
  assert.equal(speaker.speaking, false);
});

test('native synchronous play still works and cleans up once', async t => {
  const { speaker, log } = setup(t, () => {});
  speaker.end('Hello.');
  await settle();
  assert.deepEqual(log.speaking, [true]);
  log.finish();
  speaker.stop();
  assert.equal(log.cleanup, 1);
  assert.equal(log.removed, 1);
});

test('browser adapter returns the actual asynchronous permission error', async () => {
  let paused = false;
  const media = {
    play: () => Promise.reject(new DOMException('Not allowed', 'NotAllowedError')),
    pause: () => { paused = true; }, load() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {},
  };
  const player = createBrowserTtsPlayer(media, 'test-audio');
  await assert.rejects(player.play(), { name: 'NotAllowedError' });
  player.remove();
  assert.equal(paused, true);
});