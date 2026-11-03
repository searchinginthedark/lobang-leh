// Picks the look before first paint, so the page never flashes the other one. Two looks:
// 'ios' (default: native iOS, after the App Store Today tab) and 'sticker' (Sticker Scrapbook,
// docs/restyle-contract.md). The choice is a class on <html>; app.css scopes the iOS look under
// html.ios. An external file, not an inline script: CSP is script-src 'self'.
(function () {
  var KEY = 'lobang:skin';
  var root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  // The browser chrome / status bar matches each look's page background.
  function paintThemeColor() {
    var m = document.querySelector('meta[name="theme-color"]');
    if (!m) return;
    var dark = !!(mq && mq.matches);
    m.setAttribute('content', root.classList.contains('ios') ? (dark ? '#000000' : '#f2f2f7') : '#c82626');
  }
  function apply(s) {
    root.classList.toggle('ios', s === 'ios');
    paintThemeColor();
  }

  var saved = null;
  try { saved = window.localStorage.getItem(KEY); } catch (e) { /* private mode */ }
  apply(saved === 'sticker' ? 'sticker' : 'ios');
  if (mq) {
    if (mq.addEventListener) mq.addEventListener('change', paintThemeColor);
    else if (mq.addListener) mq.addListener(paintThemeColor);
  }

  window.LobangSkin = {
    get: function () { return root.classList.contains('ios') ? 'ios' : 'sticker'; },
    set: function (s) {
      apply(s);
      try { window.localStorage.setItem(KEY, s); } catch (e) { /* ignore */ }
    }
  };
})();
