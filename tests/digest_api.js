// node tests/digest_api.js - run by tests/test_digest.py. Exit 0 = every check passed.
const assert = require('assert');
const path = require('path');
const D = require(path.join(__dirname, '..', 'api', '_digest.js'));

function store(init) {
  const kv = Object.assign({}, init || {});
  const hashes = { 'lobang:subs': {} };
  const calls = [];
  async function cmd(...a) {
    calls.push(a);
    const [op, key] = a;
    if (op === 'SET') {
      if (a.includes('NX') && key in kv) return null;
      kv[key] = a[2];
      return 'OK';
    }
    if (op === 'DEL') { delete kv[key]; return 1; }
    if (op === 'GET') return kv[key] || null;
    if (op === 'HGETALL') {
      if (store.failRead) throw new Error('redis 500');
      return Object.entries(hashes[key] || {}).flat();
    }
    if (op === 'HDEL') { a.slice(2).forEach((f) => delete hashes[key][f]); return 1; }
    throw new Error('unexpected ' + op);
  }
  return { kv, hashes, calls, cmd };
}
const sub = (n) => JSON.stringify({ sub: { endpoint: 'https://push.example/' + n, keys: { p256dh: 'p', auth: 'a' } } });
const B = { day: '2026-10-22', title: '3 new lobangs today', body: '• a\n• b\n• c', ids: ['x'] };

(async () => {
  // auth: exact secret only, Bearer scheme only, an unset secret never authorises
  assert.ok(D.authorized('Bearer s3cret', 's3cret'));
  assert.ok(!D.authorized('Bearer s3cre', 's3cret'));
  assert.ok(!D.authorized('s3cret', 's3cret'));
  assert.ok(!D.authorized('Bearer ', ''));
  assert.ok(!D.authorized(undefined, 's3cret'));

  // body validation
  assert.ok(D.validBody(B));
  assert.ok(!D.validBody(Object.assign({}, B, { day: '22 Oct' })));
  assert.ok(!D.validBody(Object.assign({}, B, { title: '' })));
  assert.ok(!D.validBody(Object.assign({}, B, { body: 'x'.repeat(401) })));

  // sends to every subscriber once, prunes 410, records the run
  let s = store();
  s.hashes['lobang:subs'] = { a: sub('a'), b: sub('b'), c: sub('c'), bad: '{nope' };
  const sentTo = [];
  const send = async (sb, payload) => {
    sentTo.push(sb.endpoint);
    assert.strictEqual(JSON.parse(payload).title, B.title);
    if (sb.endpoint.endsWith('/b')) { const e = new Error('gone'); e.statusCode = 410; throw e; }
    if (sb.endpoint.endsWith('/c')) { const e = new Error('flaky'); e.statusCode = 500; throw e; }
  };
  let out = await D.run(B, { cmd: s.cmd, send });
  assert.strictEqual(out.sent, 1);
  assert.strictEqual(out.failed, 2);
  assert.strictEqual(out.pruned, 1);
  assert.deepStrictEqual(Object.keys(s.hashes['lobang:subs']).sort(), ['a', 'bad', 'c']);   // 500 kept, 410 pruned
  assert.strictEqual(JSON.parse(s.kv['lobang:digest:last']).sent, 1);

  // a second call the same day pushes nothing
  sentTo.length = 0;
  out = await D.run(B, { cmd: s.cmd, send });
  assert.strictEqual(out.skipped, 'already_sent');
  assert.strictEqual(sentTo.length, 0);

  // the next day sends again
  out = await D.run(Object.assign({}, B, { day: '2026-10-23' }), { cmd: s.cmd, send });
  assert.strictEqual(out.ok, true);
  assert.ok(sentTo.length > 0);

  // an unreadable subscriber list releases the lock so the next collect retries
  s = store();
  store.failRead = true;
  await assert.rejects(D.run(B, { cmd: s.cmd, send }));
  assert.ok(!('lobang:digest:2026-10-22' in s.kv), 'lock must be released');
  store.failRead = false;
  s.hashes['lobang:subs'] = { a: sub('a') };
  out = await D.run(B, { cmd: s.cmd, send: async () => {} });
  assert.strictEqual(out.sent, 1);

  // no subscribers: the day counts as done, nothing sent
  s = store();
  out = await D.run(B, { cmd: s.cmd, send: async () => { throw new Error('must not send'); } });
  assert.strictEqual(out.sent, 0);

  // subscription validation and stable ids
  assert.ok(D.validSub({ endpoint: 'https://x', keys: { p256dh: 'p', auth: 'a' } }));
  assert.ok(!D.validSub({ endpoint: 'http://x', keys: { p256dh: 'p', auth: 'a' } }));
  assert.ok(!D.validSub({ endpoint: 'https://x' }));
  assert.strictEqual(D.subId('https://x'), D.subId('https://x'));
  assert.strictEqual(D.subId('https://x').length, 24);

  console.log('digest_api: ok');
})().catch((e) => { console.error(e); process.exit(1); });
