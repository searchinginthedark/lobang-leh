// paved:memo app=lobang-leh body=fe3f8ef030ca - generated from memory/tools/paved/sources/memo.js; edit there, then run: python memory/tools/paved/paved.py sync
// paved:app-begin (this app's own notes; kept verbatim by paved.py sync)
// paved:app-end
// One short-lived copy of a store read, per serverless instance, for a route anyone can call
// without a credential. Every such call used to spend commands on the Upstash database most of
// the fleet shares (500K a month), so a stranger's loop could use up that month for every app.
// With this, a warm instance reads the store at most 12 times an hour however often it is asked.
//
// Only a read you keep is copied. A failed read throws straight through and a kept:false read is
// returned uncopied, so an outage still shows at once and an unknown never lingers as an answer.
// A copy can be up to TTL old, so report ageMs in the body, and work out anything that depends on
// the time (a stale tick, say) when answering, from the copied value and the current clock.
//
//   const read = memo(async () => ({ ok: true, subs: await countSubs() }), { keep: (v) => v.ok });
//   const { value, ageMs } = await read();
//
// Not for a credential check: a revoke must take effect on the next request (news-radar,
// 2026-10-18), and not for anything a scheduler acts on.
const DEFAULT_TTL_MS = 5 * 60 * 1000;

function memo(load, { ttlMs = DEFAULT_TTL_MS, keep = () => true, now = Date.now } = {}) {
  let copy = null;
  let inflight = null;

  const read = async () => {
    if (copy && now() - copy.at < ttlMs) return { value: copy.value, ageMs: now() - copy.at };
    // Callers arriving during a read share it, so a burst on a cold instance costs one read.
    if (!inflight) {
      inflight = (async () => {
        try {
          const value = await load();
          if (keep(value)) copy = { value, at: now() };
          return value;
        } finally {
          inflight = null;
        }
      })();
    }
    return { value: await inflight, ageMs: 0 };
  };
  read.reset = () => { copy = null; };
  return read;
}

module.exports = { memo, DEFAULT_TTL_MS };
