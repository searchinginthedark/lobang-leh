// Run by tests/test_embed.py: tokenises and encodes texts with public/embed.js, as the page does,
// reading the model files from disk. Prints {"ids": [[...]], "vecs": [[...]]} for the texts on stdin.
'use strict';
var fs = require('fs');
var path = require('path');
var E = require(path.join(__dirname, '..', 'public', 'embed.js'));

var root = path.join(__dirname, '..', 'public', 'embed') + path.sep;
function rel(p) { return path.join(root, p.slice('embed/'.length)); }
var m = E.create(
  function (p) { return Promise.resolve(fs.readFileSync(rel(p), 'utf8')); },
  function (p) { var b = fs.readFileSync(rel(p)); return Promise.resolve(b.buffer.slice(b.byteOffset, b.byteOffset + b.length)); }
);
var texts = JSON.parse(fs.readFileSync(0, 'utf8'));
m.load().then(function () {
  var ids = texts.map(function (t) { return m.tokenize(t); });
  return Promise.all(texts.map(function (t) { return m.encode(t); })).then(function (vs) {
    process.stdout.write(JSON.stringify({ ids: ids, vecs: vs.map(function (v) { return v ? Array.from(v) : null; }) }));
  });
}).catch(function (e) { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
