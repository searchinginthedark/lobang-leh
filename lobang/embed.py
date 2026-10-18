"""Text embeddings for semantic search, with no model runtime and no network.

The model is minishlab/potion-retrieval-32M, a STATIC embedding model (model2vec): a text's
vector is the mean of its tokens' vectors, L2-normalised. That is the whole forward pass, so the
same arithmetic runs here (CI, embedding every deal) and in public/app.js (the phone, embedding
the query), and both read the same files:

  public/embed/vocab.txt    one WordPiece token per line; line n is token id n
  public/embed/t/<k>.bin    tokens 64k .. 64k+63: per token a float32 scale + DIM int8 values

tools/build_embed_model.py writes those files once (PCA 512 -> 256 dims, int8 per row). The
phone fetches only the shards its query's tokens live in. Tokenisation mirrors the model's
HuggingFace tokenizer (BertNormalizer + BertPreTokenizer + WordPiece) and is pinned against it by
tests/fixtures/embed_tokens.json, in Python and in JS.
"""

from __future__ import annotations

import io
import math
import os
import struct
import unicodedata

DIM = 256
SHARD = 64
MAX_TOKENS = 512          # model2vec's default truncation
MAX_WORD_CHARS = 100      # WordPiece max_input_chars_per_word
UNK = "[UNK]"
MODEL = "potion-retrieval-32M/pca256/int8"

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "embed")


def _is_control(ch):
    if ch in "\t\n\r":
        return False
    return unicodedata.category(ch) in ("Cc", "Cf")


def _is_cjk(cp):
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF
            or 0x2A700 <= cp <= 0x2B73F or 0x2B740 <= cp <= 0x2B81F or 0x2B820 <= cp <= 0x2CEAF
            or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)


def _is_punct(ch):
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


def normalize(text):
    """BertNormalizer(clean_text, handle_chinese_chars, strip_accents=None -> follows lowercase)."""
    out = []
    for ch in text:
        cp = ord(ch)
        if cp == 0 or cp == 0xFFFD or _is_control(ch):
            continue
        if ch.isspace():
            out.append(" ")
        elif _is_cjk(cp):
            out.append(" " + ch + " ")
        else:
            out.append(ch)
    s = unicodedata.normalize("NFD", "".join(out))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def pre_tokenize(text):
    """BertPreTokenizer: split on whitespace, and every punctuation char is its own word."""
    words, cur = [], []
    for ch in text:
        if ch.isspace():
            if cur:
                words.append("".join(cur))
                cur = []
        elif _is_punct(ch):
            if cur:
                words.append("".join(cur))
                cur = []
            words.append(ch)
        else:
            cur.append(ch)
    if cur:
        words.append("".join(cur))
    return words


class Model:
    def __init__(self, vocab, table):
        self.vocab = vocab                      # token -> id
        self.table = table                      # id -> (scale, bytes of DIM int8)
        self.unk = vocab.get(UNK)

    @classmethod
    def load(cls, root=ROOT):
        with io.open(os.path.join(root, "vocab.txt"), encoding="utf-8") as fh:
            tokens = fh.read().split("\n")
        if tokens and tokens[-1] == "":
            tokens.pop()
        vocab = {t: i for i, t in enumerate(tokens)}
        table = {}
        row = 4 + DIM
        for k in range((len(tokens) + SHARD - 1) // SHARD):
            with open(os.path.join(root, "t", "{0}.bin".format(k)), "rb") as fh:
                buf = fh.read()
            for j in range(len(buf) // row):
                off = j * row
                (scale,) = struct.unpack_from("<f", buf, off)
                table[k * SHARD + j] = (scale, buf[off + 4: off + row])
        return cls(vocab, table)

    def wordpiece(self, word):
        if len(word) > MAX_WORD_CHARS:
            return [self.unk]
        ids, start = [], 0
        while start < len(word):
            end, hit = len(word), None
            while start < end:
                piece = word[start:end] if start == 0 else "##" + word[start:end]
                if piece in self.vocab:
                    hit = self.vocab[piece]
                    break
                end -= 1
            if hit is None:
                return [self.unk]
            ids.append(hit)
            start = end
        return ids

    def tokenize(self, text):
        """Token ids with [UNK] removed (model2vec drops it), truncated to MAX_TOKENS."""
        ids = []
        for w in pre_tokenize(normalize(text or "")):
            ids.extend(i for i in self.wordpiece(w) if i != self.unk)
        return ids[:MAX_TOKENS]

    def encode(self, text):
        """Unit vector (list of DIM floats), or None when no token is known."""
        ids = [i for i in self.tokenize(text) if i in self.table]
        if not ids:
            return None
        acc = [0.0] * DIM
        for i in ids:
            scale, raw = self.table[i]
            for d, b in enumerate(raw):
                acc[d] += scale * (b - 256 if b > 127 else b)
        n = math.sqrt(sum(x * x for x in acc))
        if n == 0:
            return None
        return [x / n for x in acc]


def quantize(vec):
    """Unit vector -> DIM signed bytes (x127), for the published vector file."""
    return bytes((max(-127, min(127, int(round(x * 127)))) & 0xFF) for x in vec)


def deal_text(d):
    """What a deal's vector is made of: its merchants, headline and the source's own text.
    Only the opening of the body counts: a mean over a 5,000-char listicle is the listicle's
    average topic, not this deal's."""
    parts = [" ".join(d.get("merchants") or []), d.get("title") or "", d.get("summary") or ""]
    body = d.get("body") or ""
    if body:
        parts.append(body[:600])
    return ". ".join(p for p in parts if p)
