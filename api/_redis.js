// Upstash Redis over plain HTTPS. Files prefixed with "_" under api/ are not
// exposed as endpoints.
//
// Taken from AreYouAtHome's api/_redis.js (2026-10-21), not the paved _kv.js:
// subscriptions are hash fields, so a subscribe and a prune never rewrite one
// whole document over each other.
//
// Every failure THROWS. A read that could not be served must never come back
// as "no subscribers": the digest would mark the day sent and push nobody.
//
// Shares the hydrate/curfew/Fleetly/AreYouAtHome Upstash database (user
// ruling 2026-10-21), every key prefixed "lobang:". The free tier is a MONTHLY
// allowance shared by all of them; the digest costs ~4 commands a day.

const NET_TIMEOUT_MS = 8000;

function config() {
  // Vercel's Upstash marketplace integration names them KV_*; a hand-made
  // database uses the UPSTASH_* names. Accept either.
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL || '';
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || '';
  return { url: String(url).replace(/\/+$/, ''), token };
}

// Swapped in by dev/server.js for local runs. Never set in production.
let driver = null;

function configured() {
  if (driver) return true;
  const c = config();
  return !!(c.url && c.token);
}

async function post(path, body) {
  const { url, token } = config();
  if (!url || !token) throw new Error('store_not_configured');
  const r = await fetch(url + path, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
    signal: AbortSignal.timeout(NET_TIMEOUT_MS)
  });
  if (!r.ok) throw new Error('redis ' + r.status);
  return r.json();
}

// One command: cmd('HSET', 'key', 'field', 'value')
async function cmd(...args) {
  if (driver) return driver([args.map(String)])[0];
  const j = await post('', args.map(String));
  if (j.error) throw new Error('redis ' + j.error);
  return j.result;
}

// Several commands in one round trip. Throws if ANY of them failed, so a
// caller never acts on half a read.
async function pipeline(cmds) {
  const list = cmds.map((c) => c.map(String));
  if (driver) return driver(list);
  const j = await post('/pipeline', list);
  if (!Array.isArray(j) || j.length !== list.length) throw new Error('redis bad_pipeline');
  return j.map((x) => {
    if (x.error) throw new Error('redis ' + x.error);
    return x.result;
  });
}

// HGETALL answers a flat [field, value, field, value] array over REST.
function pairs(flat) {
  const out = {};
  if (!Array.isArray(flat)) return out;
  for (let i = 0; i + 1 < flat.length; i += 2) out[flat[i]] = flat[i + 1];
  return out;
}

module.exports = { cmd, pipeline, pairs, configured, _setDriver: (d) => { driver = d; } };
