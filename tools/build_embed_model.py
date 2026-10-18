"""One-off: turn minishlab/potion-retrieval-32M into the static files lobang.embed and app.js read.

    pip install model2vec==0.7.0     # this tool only; CI and the page never need it
    python tools/build_embed_model.py [--check]

Writes public/embed/vocab.txt + public/embed/t/<k>.bin (format in lobang/embed.py) and
tests/fixtures/embed_tokens.json (HuggingFace's own token ids for sample texts, which pin both
tokenizer ports). PCA 512 -> 256 halves the download; projecting UNcentred rows keeps the model
linear, so the mean of projected tokens is the projection of the mean.

--check compares the shipped files against the full float32 model on the stored deal texts: top-5
agreement and cosine error, so a shrink that hurts ranking is measured, not assumed.
"""

from __future__ import annotations

import io
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lobang import embed as E  # noqa: E402

NAME = "minishlab/potion-retrieval-32M"
FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures", "embed_tokens.json")
SAMPLES = [
    "McDonald's 1-for-1 McSpicy via app till 12 Oct",
    "LiHo: Free bubble tea!! 🧋 (members only)",
    "Café Mosaic (Carlton Hotel Singapore): 50% off Buffets",
    "Häagen-Dazs S$3.90 cones — today only, 10am–2pm",
    "新开 Hai Di Lao 海底捞 at Jewel Changi #01-36",
    "free food", "cheap coffee near orchard", "japanese ramen new opening",
    "supercalifragilisticexpialidocious" * 4,
    "Tab\tand\nnewline  spaces nbsp​zwsp",
]


def build():
    from model2vec import StaticModel
    m = StaticModel.from_pretrained(NAME)
    emb = np.asarray(m.embedding, dtype=np.float64)
    tok = json.loads(m.tokenizer.to_str())["model"]["vocab"]
    tokens = [None] * len(tok)
    for t, i in tok.items():
        tokens[i] = t
    assert all(t is not None and "\n" not in t for t in tokens), "vocab ids are not dense, or a token has a newline"

    centred = emb - emb.mean(axis=0)
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    proj = emb @ vt[:E.DIM].T
    scale = np.abs(proj).max(axis=1) / 127.0
    scale[scale == 0] = 1.0
    q = np.clip(np.round(proj / scale[:, None]), -127, 127).astype(np.int8)

    os.makedirs(os.path.join(E.ROOT, "t"), exist_ok=True)
    with io.open(os.path.join(E.ROOT, "vocab.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(tokens) + "\n")
    for k in range((len(tokens) + E.SHARD - 1) // E.SHARD):
        with open(os.path.join(E.ROOT, "t", "{0}.bin".format(k)), "wb") as fh:
            for i in range(k * E.SHARD, min(len(tokens), (k + 1) * E.SHARD)):
                fh.write(struct.pack("<f", float(scale[i])))
                fh.write(q[i].tobytes())

    cases = [{"text": s, "ids": [i for i in m.tokenizer.encode(s, add_special_tokens=False).ids if i != m.unk_token_id]}
             for s in SAMPLES]
    with io.open(FIX, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"model": NAME, "cases": cases}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote {0} tokens in {1} shards, dim {2}".format(len(tokens), k + 1, E.DIM))


def check():
    from model2vec import StaticModel
    m = StaticModel.from_pretrained(NAME)
    small = E.Model.load()
    deals = json.load(io.open("public/deals.json", encoding="utf-8"))["deals"]
    texts = [E.deal_text(d) for d in deals]
    bad = [t for t in texts if small.tokenize(t) != [i for i in m.tokenizer.encode(t, add_special_tokens=False).ids
                                                    if i != m.unk_token_id][:E.MAX_TOKENS]]
    print("tokenizer mismatches: {0} of {1}".format(len(bad), len(texts)))
    for t in bad[:3]:
        print("  ", t[:120])
    full = m.encode(texts)
    full /= np.linalg.norm(full, axis=1, keepdims=True)
    mine = np.array([small.encode(t) for t in texts])
    queries = ["free food", "cheap coffee", "bubble tea 1-for-1", "japanese ramen new opening", "korean fried chicken",
               "buffet discount", "dessert under $5", "birthday free cake", "halal", "student meal", "new cafe in the east",
               "mala", "pizza", "dim sum", "free drinks with no minimum spend"]
    agree = []
    for qtext in queries:
        a = m.encode([qtext])[0]
        a /= np.linalg.norm(a)
        b = np.array(small.encode(qtext))
        ta, tb = set(np.argsort(-(full @ a))[:5]), set(np.argsort(-(mine @ b))[:5])
        agree.append(len(ta & tb) / 5.0)
        print("  {0:<36} top-5 overlap {1:.0%}".format(qtext, agree[-1]))
    print("mean top-5 overlap {0:.0%}".format(sum(agree) / len(agree)))


if __name__ == "__main__":
    check() if "--check" in sys.argv else build()
