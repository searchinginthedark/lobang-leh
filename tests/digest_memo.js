// node tests/digest_memo.js - run by tests/test_digest.py. Exit 0 = every check passed.
// GET /api/digest takes no credential and reads the shared database, so repeated calls must
// not each spend a command.
const assert = require('assert');
const Module = require('module');
const path = require('path');

// The GET path never sends a push, so this runs without web-push installed.
const realLoad = Module._load;
Module._load = function (name, ...rest) {
  return name === 'web-push' ? {} : realLoad.call(this, name, ...rest);
};

const api = (f) => path.join(__dirname, '..', 'api', f);
const redis = require(api('_redis.js'));
const digest = require(api('digest.js'));

function ask() {
  return new Promise((resolve, reject) => {
    const res = {
      setHeader() {},
      status(c) { this.code = c; return this; },
      json(b) { resolve({ status: this.code, body: b }); return this; },
    };
    digest({ method: 'GET', headers: {} }, res).catch(reject);
  });
}

(async () => {
  let commands = 0;
  let up = true;
  redis._setDriver((list) => {
    if (!up) throw new Error('redis 503');
    commands += list.length;
    return list.map(() => JSON.stringify({ day: '2026-11-06', sent: 3 }));
  });

  for (let i = 0; i < 50; i++) {
    const r = await ask();
    assert.strictEqual(r.status, 200);
    assert.strictEqual(r.body.ok, true);
    assert.strictEqual(r.body.last.sent, 3);
  }
  assert.strictEqual(commands, 1, '50 calls should cost one command, cost ' + commands);

  // A failed read answers degraded, is not kept, and recovery shows on the next call.
  digest._readLast.reset();
  up = false;
  const down = await ask();
  assert.deepStrictEqual([down.status, down.body.ok, down.body.degraded], [200, false, 'store_unavailable']);
  up = true;
  assert.strictEqual((await ask()).body.ok, true);
  console.log('digest_memo: ok');
})().catch((e) => { console.error(e); process.exit(1); });
