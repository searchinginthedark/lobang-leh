// POST   /api/subscribe  { sub }       this phone gets the morning digest
// DELETE /api/subscribe  { endpoint }  it stops
//
// No account: the subscription itself is the only thing stored (endpoint + keys, which only the
// push service can use), keyed by a hash of the endpoint. A 200 is what the page shows as "on",
// sent only once the store confirms the write.
const { cmd, configured } = require('./_redis');
const D = require('./_digest');

function body(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  try { return JSON.parse(req.body || '{}'); } catch (e) { return {}; }
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST' && req.method !== 'DELETE') return res.status(405).json({ error: 'method_not_allowed' });
  if (!configured()) return res.status(503).json({ error: 'store_not_configured' });
  const b = body(req);

  if (req.method === 'DELETE') {
    if (typeof b.endpoint !== 'string' || b.endpoint.length > 1024) return res.status(400).json({ error: 'bad_endpoint' });
    try {
      await cmd('HDEL', D.KEYS.subs, D.subId(b.endpoint));
    } catch (e) {
      return res.status(503).json({ error: 'store_unavailable' });
    }
    return res.status(200).json({ ok: true });
  }

  if (!D.validSub(b.sub)) return res.status(400).json({ error: 'bad_subscription' });
  const id = D.subId(b.sub.endpoint);
  try {
    // Fail closed at the cap rather than evicting someone else's phone.
    if (Number(await cmd('HLEN', D.KEYS.subs)) >= D.MAX_SUBS && !Number(await cmd('HEXISTS', D.KEYS.subs, id))) {
      return res.status(507).json({ error: 'too_many_devices' });
    }
    const entry = { sub: { endpoint: b.sub.endpoint, keys: { p256dh: b.sub.keys.p256dh, auth: b.sub.keys.auth } }, at: Date.now() };
    await cmd('HSET', D.KEYS.subs, id, JSON.stringify(entry));
  } catch (e) {
    return res.status(503).json({ error: 'store_unavailable' });
  }
  return res.status(200).json({ ok: true });
};
