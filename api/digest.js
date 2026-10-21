// @cron-facing: called by the collect workflow (lobang.digest) after every collect.
//
// POST /api/digest  Authorization: Bearer DIGEST_SECRET
//                   { day: "YYYY-MM-DD", title, body, ids }  -> push it to every subscriber, once per day
// GET  /api/digest  -> { ok, last }: the last run's counts, for a health check. No secrets, no subscribers.
//
// A backend problem answers 200 {ok:false, degraded} (never 5xx): the caller is a scheduler, and
// the next collect retries because the day's lock is only kept once the subscriber list was read.
// Pushes go out BEFORE the response: Vercel may freeze the function the moment it responds.
const webpush = require('web-push');
const { cmd, configured } = require('./_redis');
const D = require('./_digest');

const SEND_TIMEOUT_MS = 6000;

// Why the store failed, as a code that can never echo the URL or token: "Failed to parse URL from
// <url>" would print the URL, so messages are classified, not passed through.
function storeReason(e) {
  const m = String((e && e.message) || '');
  if (/^redis \d{3}$/.test(m)) return 'http_' + m.slice(6);
  if (/parse URL|Invalid URL/i.test(m)) return 'bad_url';
  if (e && (e.name === 'TimeoutError' || e.name === 'AbortError')) return 'timeout';
  if (/^redis /.test(m)) return 'redis_error';
  return 'network';
}

function body(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  try { return JSON.parse(req.body || '{}'); } catch (e) { return {}; }
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'GET') {
    if (!configured()) return res.status(200).json({ ok: false, degraded: 'store_not_configured' });
    try {
      const raw = await cmd('GET', D.KEYS.last);
      return res.status(200).json({ ok: true, last: raw ? JSON.parse(raw) : null });
    } catch (e) {
      return res.status(200).json({ ok: false, degraded: 'store_unavailable', reason: storeReason(e) });
    }
  }
  if (req.method !== 'POST') return res.status(405).json({ error: 'method_not_allowed' });
  if (!D.authorized(req.headers.authorization, process.env.DIGEST_SECRET)) return res.status(401).json({ error: 'unauthorized' });
  const b = body(req);
  if (!D.validBody(b)) return res.status(400).json({ error: 'bad_body' });

  const pub = process.env.VAPID_PUBLIC_KEY, priv = process.env.VAPID_PRIVATE_KEY;
  if (!pub || !priv) return res.status(200).json({ ok: false, degraded: 'vapid_not_configured' });
  if (!configured()) return res.status(200).json({ ok: false, degraded: 'store_not_configured' });
  webpush.setVapidDetails(process.env.VAPID_SUBJECT || 'mailto:lobang-leh@example.com', pub, priv);

  try {
    const out = await D.run(b, {
      cmd,
      send: (sub, payload) => webpush.sendNotification(sub, payload, { TTL: 8 * 3600, urgency: 'normal', timeout: SEND_TIMEOUT_MS })
    });
    return res.status(200).json(out);
  } catch (e) {
    return res.status(200).json({ ok: false, degraded: 'store_unavailable', reason: storeReason(e) });
  }
};
