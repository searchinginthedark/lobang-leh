// Query embeddings for semantic search: the browser half of lobang/embed.py (read its docstring).
// A static model, so a query's vector is the mean of its tokens' rows, L2-normalised. Only the
// shards holding the query's tokens are fetched (about 17 KB each), then kept by the service worker.
// Tokenisation mirrors the model's BertNormalizer + BertPreTokenizer + WordPiece, and is pinned
// against HuggingFace's own token ids by tests/test_embed.py (which runs this file in Node).
var LobangEmbed = (function () {
  'use strict';

  var DIM = 256, SHARD = 64, MAX_TOKENS = 512, MAX_WORD = 100, UNK = '[UNK]';
  var CTRL = /[\p{Cc}\p{Cf}]/u, MARK = /\p{Mn}/gu, PUNCT = /\p{P}/u, SPACE = /\s/;

  function isCjk(c) {
    return (c >= 0x4E00 && c <= 0x9FFF) || (c >= 0x3400 && c <= 0x4DBF) || (c >= 0x20000 && c <= 0x2A6DF) ||
      (c >= 0x2A700 && c <= 0x2B73F) || (c >= 0x2B740 && c <= 0x2B81F) || (c >= 0x2B820 && c <= 0x2CEAF) ||
      (c >= 0xF900 && c <= 0xFAFF) || (c >= 0x2F800 && c <= 0x2FA1F);
  }
  function isPunct(ch) {
    var c = ch.codePointAt(0);
    return (c >= 33 && c <= 47) || (c >= 58 && c <= 64) || (c >= 91 && c <= 96) || (c >= 123 && c <= 126) || PUNCT.test(ch);
  }

  function normalize(text) {
    var out = '';
    for (var ch of String(text || '')) {
      var c = ch.codePointAt(0);
      if (c === 0 || c === 0xFFFD || (CTRL.test(ch) && ch !== '\t' && ch !== '\n' && ch !== '\r')) continue;
      if (SPACE.test(ch)) out += ' ';
      else if (isCjk(c)) out += ' ' + ch + ' ';
      else out += ch;
    }
    return out.normalize('NFD').replace(MARK, '').toLowerCase();
  }

  // Words as arrays of code points: WordPiece counts and slices characters, not UTF-16 units.
  function preTokenize(text) {
    var words = [], cur = [];
    for (var ch of text) {
      if (SPACE.test(ch)) { if (cur.length) { words.push(cur); cur = []; } }
      else if (isPunct(ch)) { if (cur.length) { words.push(cur); cur = []; } words.push([ch]); }
      else cur.push(ch);
    }
    if (cur.length) words.push(cur);
    return words;
  }

  function create(getText, getBuffer, base) {
    base = base || 'embed/';
    var vocab = null, unk = -1, shards = {}, loading = null;

    function load() {
      if (!loading) {
        loading = getText(base + 'vocab.txt').then(function (txt) {
          var lines = txt.split('\n');
          if (lines[lines.length - 1] === '') lines.pop();
          vocab = new Map();
          for (var i = 0; i < lines.length; i++) vocab.set(lines[i], i);
          unk = vocab.has(UNK) ? vocab.get(UNK) : -1;
        });
        loading.catch(function () { loading = null; });   // a failed load can be retried later
      }
      return loading;
    }

    function wordpiece(chars) {
      if (chars.length > MAX_WORD) return [unk];
      var ids = [], start = 0;
      while (start < chars.length) {
        var end = chars.length, hit = -1;
        while (start < end) {
          var piece = (start === 0 ? '' : '##') + chars.slice(start, end).join('');
          if (vocab.has(piece)) { hit = vocab.get(piece); break; }
          end--;
        }
        if (hit < 0) return [unk];
        ids.push(hit);
        start = end;
      }
      return ids;
    }

    // Token ids with [UNK] removed (model2vec drops it), truncated to MAX_TOKENS. Call after load().
    function tokenize(text) {
      var ids = [];
      preTokenize(normalize(text)).forEach(function (w) {
        wordpiece(w).forEach(function (i) { if (i !== unk) ids.push(i); });
      });
      return ids.slice(0, MAX_TOKENS);
    }

    function shard(k) {
      if (!shards[k]) {
        shards[k] = getBuffer(base + 't/' + k + '.bin');
        shards[k].catch(function () { delete shards[k]; });
      }
      return shards[k];
    }

    // Unit vector (Float64Array of DIM), or null when no token of the text is known.
    function encode(text) {
      return load().then(function () {
        var ids = tokenize(text);
        if (!ids.length) return null;
        var need = {};
        ids.forEach(function (i) { need[Math.floor(i / SHARD)] = true; });
        var ks = Object.keys(need);
        return Promise.all(ks.map(function (k) { return shard(+k); })).then(function (bufs) {
          var byK = {};
          ks.forEach(function (k, n) { byK[k] = bufs[n]; });
          var acc = new Float64Array(DIM), row = 4 + DIM;
          ids.forEach(function (i) {
            var buf = byK[Math.floor(i / SHARD)], off = (i % SHARD) * row;
            var dv = new DataView(buf, off, row), scale = dv.getFloat32(0, true);
            var q = new Int8Array(buf, off + 4, DIM);
            for (var d = 0; d < DIM; d++) acc[d] += scale * q[d];
          });
          var n = 0;
          for (var d = 0; d < DIM; d++) n += acc[d] * acc[d];
          n = Math.sqrt(n);
          if (!n) return null;
          for (var e = 0; e < DIM; e++) acc[e] /= n;
          return acc;
        });
      });
    }

    return { load: load, tokenize: tokenize, encode: encode };
  }

  // A published deal vector: base64 of DIM signed bytes, the unit vector x127.
  function decode(b64) {
    var s = atob(b64), out = new Int8Array(s.length);
    for (var i = 0; i < s.length; i++) out[i] = (s.charCodeAt(i) << 24) >> 24;
    return out;
  }
  function cosine(q, v) {
    var s = 0;
    for (var i = 0; i < v.length; i++) s += q[i] * v[i];
    return s / 127;
  }

  return { create: create, decode: decode, cosine: cosine, normalize: normalize, DIM: DIM };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = LobangEmbed;
