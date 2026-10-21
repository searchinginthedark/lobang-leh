// Morning digest logic, kept free of I/O so tests/digest_api.js can drive it with a fake store.
//
// The day's push is guarded by SET NX on lobang:digest:<day>: every collect inside the send
// window calls /api/digest, and only the first one each day may push. A lock is released only
// when the subscriber list could not be read, so the next collect retries instead of the day
// being marked sent with nobody told.
const crypto = require('crypto');

const KEYS = {
  subs: 'lobang:subs',                       // hash: subId -> {sub, at}
  lock: (day) => 'lobang:digest:' + day,     // "1", expires after LOCK_TTL
  last: 'lobang:digest:last'                 // JSON of the last run, read by GET /api/digest
};
const LOCK_TTL = 2 * 24 * 3600;
const MAX_SUBS = 100;   // the site is public: a cap keeps a flood of sign-ups off the shared DB
const TITLE_MAX = 80;
const BODY_MAX = 400;

function authorized(header, secret) {
  if (!secret || typeof header !== 'string' || !header.startsWith('Bearer ')) return false;
  const a = Buffer.from(header.slice(7)), b = Buffer.from(secret);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function validBody(b) {
  return !!(b && typeof b.day === 'string' && /^\d{4}-\d\d-\d\d$/.test(b.day) &&
    typeof b.title === 'string' && b.title && b.title.length <= TITLE_MAX &&
    typeof b.body === 'string' && b.body.length <= BODY_MAX);
}

function validSub(s) {
  return !!(s && typeof s.endpoint === 'string' && /^https:\/\//.test(s.endpoint) &&
    s.endpoint.length < 1024 && s.keys &&
    typeof s.keys.p256dh === 'string' && s.keys.p256dh.length < 256 &&
    typeof s.keys.auth === 'string' && s.keys.auth.length < 256);
}

function subId(endpoint) {
  return crypto.createHash('sha256').update(endpoint, 'utf8').digest('hex').slice(0, 24);
}

function pairs(flat) {
  const out = {};
  if (!Array.isArray(flat)) return out;
  for (let i = 0; i + 1 < flat.length; i += 2) out[flat[i]] = flat[i + 1];
  return out;
}

// deps: { cmd(...args) -> result, send(sub, payloadString) -> Promise (rejects with .statusCode) }
async function run(b, deps) {
  const lockKey = KEYS.lock(b.day);
  const got = await deps.cmd('SET', lockKey, '1', 'NX', 'EX', String(LOCK_TTL));
  if (got !== 'OK') return { ok: true, day: b.day, skipped: 'already_sent' };

  let subs;
  try {
    subs = pairs(await deps.cmd('HGETALL', KEYS.subs));
  } catch (e) {
    try { await deps.cmd('DEL', lockKey); } catch (e2) { /* the lock expires on its own */ }
    throw e;
  }
  const targets = [];
  for (const [id, raw] of Object.entries(subs)) {
    try { targets.push({ id, sub: JSON.parse(raw).sub }); } catch (e) { /* a bad row is skipped, never fatal */ }
  }
  const payload = JSON.stringify({ title: b.title, body: b.body, tag: 'lobang-digest', url: './' });
  const gone = [];
  let sent = 0;
  await Promise.all(targets.map(async (t) => {
    try {
      await deps.send(t.sub, payload);
      sent++;
    } catch (e) {
      // 404/410: the browser dropped this subscription. Anything else may be transient.
      if (e && (e.statusCode === 404 || e.statusCode === 410)) gone.push(t.id);
    }
  }));
  if (gone.length) {
    try { await deps.cmd('HDEL', KEYS.subs, ...gone); } catch (e) { /* pruned on a later day */ }
  }
  const last = { day: b.day, sent, failed: targets.length - sent, pruned: gone.length, at: new Date().toISOString() };
  try { await deps.cmd('SET', KEYS.last, JSON.stringify(last)); } catch (e) { /* status only */ }
  return Object.assign({ ok: true }, last);
}

module.exports = { KEYS, LOCK_TTL, MAX_SUBS, authorized, validBody, validSub, subId, pairs, run };
