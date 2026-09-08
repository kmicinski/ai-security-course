#!/usr/bin/env python3
"""
spam_lab.py  --  CIS400/600 spam-classification lab.

Four spam classifiers, trained from scratch on the SMS Spam Collection, using
NOTHING but the Python 3 standard library. No numpy, no scikit-learn, no pip.
It runs on whatever machine has a `python3`.

    linear      linear regression (least squares), thresholded at 0.5
    logreg      logistic regression, trained by gradient descent
    nb          multinomial naive Bayes
    mlp         a 1-hidden-layer neural network, trained by backprop

Everything operates on sparse bag-of-words features, so even the neural net
trains in a few seconds of pure Python.

Usage
-----
    python3 spam_lab.py                      # train & evaluate all four models
    python3 spam_lab.py --model logreg       # just one model
    python3 spam_lab.py --classify "WINNER!! Claim your prize now"
    python3 spam_lab.py --max-features 3000 --epochs 15
    python3 spam_lab.py --data path/to/SMSSpamCollection

Data
----
Defaults to ./data/SMSSpamCollection (the UCI SMS Spam Collection, vendored in
this repo). Format: one message per line, "<label>\\t<text>", label in
{ham, spam}. See data/UCI-README.txt for the dataset's origin and citation.
"""

import argparse
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "data", "SMSSpamCollection")
SEED = 400  # fixed so every run on every machine gives the same split & numbers


# --------------------------------------------------------------------------
# 1. Data
# --------------------------------------------------------------------------
def load(path):
    """Return a list of (label, text) with label 1 for spam, 0 for ham."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            label, text = line.split("\t", 1)
            label = label.strip().lower()
            if label in ("spam", "ham"):
                rows.append((1 if label == "spam" else 0, text))
    if not rows:
        sys.exit(f"No usable rows in {path} (expected '<label>\\t<text>' lines).")
    return rows


def split(rows, test_frac=0.2):
    """Deterministic stratified split so class balance is preserved."""
    rng = random.Random(SEED)
    spam = [r for r in rows if r[0] == 1]
    ham = [r for r in rows if r[0] == 0]
    rng.shuffle(spam)
    rng.shuffle(ham)

    def cut(xs):
        k = int(len(xs) * (1 - test_frac))
        return xs[:k], xs[k:]

    s_tr, s_te = cut(spam)
    h_tr, h_te = cut(ham)
    train = s_tr + h_tr
    test = s_te + h_te
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


# --------------------------------------------------------------------------
# 2. Features: sparse bag-of-words
# --------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[a-z0-9']+|[!$?#£]")


def tokenize(text):
    """Lowercase, then keep word-ish tokens plus a few spammy symbols.

    We deliberately keep '!' '$' '£' '#' '?' as their own tokens -- they carry
    a lot of the spam signal, and dropping them (as a naive word tokenizer
    would) throws that away.
    """
    return TOKEN_RE.findall(text.lower())


def build_vocab(train, max_features):
    """Pick the `max_features` most frequent tokens from the training set."""
    freq = {}
    for _, text in train:
        for tok in set(tokenize(text)):  # document frequency
            freq[tok] = freq.get(tok, 0) + 1
    ordered = sorted(freq, key=lambda t: (-freq[t], t))[:max_features]
    return {tok: i for i, tok in enumerate(ordered)}


def featurize(text, vocab):
    """Sparse count vector as a dict {feature_id: count}."""
    vec = {}
    for tok in tokenize(text):
        j = vocab.get(tok)
        if j is not None:
            vec[j] = vec.get(j, 0) + 1
    return vec


def prepare(rows, vocab):
    return [(featurize(t, vocab), y) for y, t in rows]


# --------------------------------------------------------------------------
# 3. Models  (each exposes .fit(data), .proba(feat) -> P(spam))
# --------------------------------------------------------------------------
def sigmoid(z):
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


class LinearRegression:
    """Least squares on {0,1} labels; a spam "score" thresholded at 0.5.

    This is the wrong tool on purpose -- it fits a line to a yes/no label, so
    its output is an unbounded score, not a probability. It still classifies
    surprisingly well, which is the point: see the slides on why we move to
    logistic regression anyway.
    """

    name = "linear regression (least squares)"

    def __init__(self, dim, lr=0.01, epochs=10, l2=1e-4):
        # A smaller learning rate than logistic regression on purpose: squared
        # error on raw counts is easy to destabilize (try lr=0.05 and watch the
        # F1 fall apart). That fragility is itself part of the lesson.
        self.w = [0.0] * dim
        self.b = 0.0
        self.lr, self.epochs, self.l2 = lr, epochs, l2

    def fit(self, data):
        rng = random.Random(SEED)
        for _ in range(self.epochs):
            rng.shuffle(data)
            for feat, y in data:
                pred = self.b + sum(self.w[i] * c for i, c in feat.items())
                err = pred - y  # d/dpred of 1/2 (pred - y)^2
                for i, c in feat.items():
                    self.w[i] -= self.lr * (err * c + self.l2 * self.w[i])
                self.b -= self.lr * err
        return self

    def score(self, feat):
        return self.b + sum(self.w[i] * c for i, c in feat.items())

    def proba(self, feat):
        # not a real probability; clamp the score to [0,1] just for reporting
        return min(1.0, max(0.0, self.score(feat)))


class LogisticRegression:
    """The workhorse. Sigmoid of a linear score, trained by gradient descent
    on cross-entropy -- exactly the update derived in the lecture."""

    name = "logistic regression (gradient descent)"

    def __init__(self, dim, lr=0.1, epochs=10, l2=1e-4):
        self.w = [0.0] * dim
        self.b = 0.0
        self.lr, self.epochs, self.l2 = lr, epochs, l2

    def fit(self, data):
        rng = random.Random(SEED)
        for _ in range(self.epochs):
            rng.shuffle(data)
            for feat, y in data:
                z = self.b + sum(self.w[i] * c for i, c in feat.items())
                g = sigmoid(z) - y  # gradient of cross-entropy wrt z is (p - y)
                for i, c in feat.items():
                    self.w[i] -= self.lr * (g * c + self.l2 * self.w[i])
                self.b -= self.lr * g
        return self

    def proba(self, feat):
        return sigmoid(self.b + sum(self.w[i] * c for i, c in feat.items()))

    def top_tokens(self, vocab, k=12):
        inv = {i: t for t, i in vocab.items()}
        order = sorted(range(len(self.w)), key=lambda i: self.w[i])
        spammy = [(inv[i], self.w[i]) for i in order[::-1][:k]]
        hammy = [(inv[i], self.w[i]) for i in order[:k]]
        return spammy, hammy


class NaiveBayes:
    """Multinomial naive Bayes with add-alpha smoothing -- the classic
    spam-filter baseline (this is the lineage of Paul Graham's 'A Plan for
    Spam')."""

    name = "multinomial naive Bayes"

    def __init__(self, dim, alpha=1.0):
        self.dim = dim
        self.alpha = alpha

    def fit(self, data):
        self.logprior = {}
        counts = {0: [0.0] * self.dim, 1: [0.0] * self.dim}
        totals = {0: 0.0, 1: 0.0}
        n = {0: 0, 1: 0}
        for feat, y in data:
            n[y] += 1
            for i, c in feat.items():
                counts[y][i] += c
                totals[y] += c
        N = n[0] + n[1]
        self.logprior = {c: math.log(n[c] / N) for c in (0, 1)}
        self.loglik = {0: [0.0] * self.dim, 1: [0.0] * self.dim}
        denom = {c: totals[c] + self.alpha * self.dim for c in (0, 1)}
        for c in (0, 1):
            for i in range(self.dim):
                self.loglik[c][i] = math.log((counts[c][i] + self.alpha) / denom[c])
        return self

    def _logscore(self, feat, c):
        s = self.logprior[c]
        for i, cnt in feat.items():
            s += cnt * self.loglik[c][i]
        return s

    def proba(self, feat):
        a = self._logscore(feat, 1)
        b = self._logscore(feat, 0)
        m = max(a, b)
        pa, pb = math.exp(a - m), math.exp(b - m)
        return pa / (pa + pb)


class MLP:
    """One hidden layer, ReLU, sigmoid output; trained by backprop. Sparse
    inputs keep it fast enough to train in pure Python. This is the same
    machinery as the neural-networks lecture, just wider."""

    name = "neural network (1 hidden layer, backprop)"

    def __init__(self, dim, hidden=16, lr=0.1, epochs=10, l2=1e-5):
        rng = random.Random(SEED)
        scale = 0.1
        # W1[j] is the weight vector (len dim) into hidden unit j
        self.W1 = [[rng.uniform(-scale, scale) for _ in range(dim)] for _ in range(hidden)]
        self.b1 = [0.0] * hidden
        self.W2 = [rng.uniform(-scale, scale) for _ in range(hidden)]
        self.b2 = 0.0
        self.hidden, self.lr, self.epochs, self.l2 = hidden, lr, epochs, l2

    def _forward(self, feat):
        z1 = list(self.b1)
        for j in range(self.hidden):
            wj = self.W1[j]
            s = 0.0
            for i, c in feat.items():
                s += wj[i] * c
            z1[j] += s
        h = [v if v > 0 else 0.0 for v in z1]  # ReLU
        z2 = self.b2 + sum(self.W2[j] * h[j] for j in range(self.hidden))
        return z1, h, sigmoid(z2)

    def fit(self, data):
        rng = random.Random(SEED)
        for _ in range(self.epochs):
            rng.shuffle(data)
            for feat, y in data:
                z1, h, p = self._forward(feat)
                d2 = p - y  # dL/dz2
                # hidden gradients
                dh = [d2 * self.W2[j] for j in range(self.hidden)]
                dz1 = [dh[j] if z1[j] > 0 else 0.0 for j in range(self.hidden)]
                # update output layer
                for j in range(self.hidden):
                    self.W2[j] -= self.lr * (d2 * h[j] + self.l2 * self.W2[j])
                self.b2 -= self.lr * d2
                # update hidden layer (only over present features)
                for j in range(self.hidden):
                    if dz1[j] == 0.0:
                        continue
                    wj = self.W1[j]
                    g = dz1[j]
                    for i, c in feat.items():
                        wj[i] -= self.lr * g * c
                    self.b1[j] -= self.lr * g
        return self

    def proba(self, feat):
        return self._forward(feat)[2]


MODELS = {
    "linear": LinearRegression,
    "logreg": LogisticRegression,
    "nb": NaiveBayes,
    "mlp": MLP,
}


# --------------------------------------------------------------------------
# 4. Evaluation
# --------------------------------------------------------------------------
def confusion(model, data, threshold=0.5):
    tp = fp = tn = fn = 0
    for feat, y in data:
        pred = 1 if model.proba(feat) >= threshold else 0
        if pred == 1 and y == 1:
            tp += 1
        elif pred == 1 and y == 0:
            fp += 1
        elif pred == 0 and y == 0:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def metrics(tp, fp, tn, fn):
    total = tp + fp + tn + fn
    acc = (tp + tn) / total if total else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return acc, prec, rec, f1


def report(name, model, test):
    tp, fp, tn, fn = confusion(model, test)
    acc, prec, rec, f1 = metrics(tp, fp, tn, fn)
    print(f"\n=== {name} ===")
    print(f"  accuracy   {acc*100:6.2f}%")
    print(f"  precision  {prec*100:6.2f}%   (of messages flagged spam, how many were)")
    print(f"  recall     {rec*100:6.2f}%   (of real spam, how much we caught)")
    print(f"  F1         {f1*100:6.2f}%")
    print(f"  confusion  TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    return acc, prec, rec, f1


def show_examples(model, test_rows, test_feats, n=6):
    """Print a handful of messages with the model's spam probability, and dig
    out its mistakes -- the interesting part."""
    print("  sample predictions:")
    for (y, text), (feat, _) in list(zip(test_rows, test_feats))[:n]:
        p = model.proba(feat)
        flag = "SPAM" if p >= 0.5 else "ham "
        truth = "spam" if y == 1 else "ham"
        print(f"    P(spam)={p:5.2f} -> {flag} | true={truth:4} | {text[:64]}")
    # first false positive and false negative, if any
    fp_shown = fn_shown = False
    for (y, text), (feat, _) in zip(test_rows, test_feats):
        p = model.proba(feat)
        pred = 1 if p >= 0.5 else 0
        if pred == 1 and y == 0 and not fp_shown:
            print(f"  false positive: P(spam)={p:.2f} | {text[:70]}")
            fp_shown = True
        if pred == 0 and y == 1 and not fn_shown:
            print(f"  false negative: P(spam)={p:.2f} | {text[:70]}")
            fn_shown = True
        if fp_shown and fn_shown:
            break


# --------------------------------------------------------------------------
# 5. Driver
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Spam classification lab (stdlib only).")
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--model", choices=list(MODELS) + ["all"], default="all")
    ap.add_argument("--max-features", type=int, default=2000)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--classify", metavar="TEXT", help="score one message and exit")
    args = ap.parse_args()

    rows = load(args.data)
    n_spam = sum(y for y, _ in rows)
    base = n_spam / len(rows)
    print(f"Loaded {len(rows)} messages: {n_spam} spam / {len(rows)-n_spam} ham "
          f"(spam base rate {base*100:.1f}%).")

    train_rows, test_rows = split(rows)
    vocab = build_vocab(train_rows, args.max_features)
    print(f"Vocabulary: {len(vocab)} tokens.  Train {len(train_rows)} / test {len(test_rows)}.")

    train = prepare(train_rows, vocab)
    test = prepare(test_rows, vocab)

    def make(key):
        cls = MODELS[key]
        if key == "nb":
            return cls(len(vocab))
        if key == "mlp":
            return cls(len(vocab), epochs=args.epochs)
        return cls(len(vocab), epochs=args.epochs)

    chosen = list(MODELS) if args.model == "all" else [args.model]

    # --classify: train logreg (or the chosen model) and score the message
    if args.classify is not None:
        key = "logreg" if args.model == "all" else args.model
        model = make(key).fit(train)
        p = model.proba(featurize(args.classify, vocab))
        verdict = "SPAM" if p >= 0.5 else "ham"
        print(f"\n[{MODELS[key].name}]  P(spam) = {p:.3f}  ->  {verdict}")
        print(f"message: {args.classify!r}")
        return

    trained = {}
    for key in chosen:
        model = make(key).fit(train)
        trained[key] = model
        report(model.name, model, test)
        show_examples(model, test_rows, test)

    if "logreg" in trained:
        spammy, hammy = trained["logreg"].top_tokens(vocab)
        print("\nlogistic-regression weights (what the model learned):")
        print("  most spammy tokens:", ", ".join(f"{t}({w:+.2f})" for t, w in spammy[:8]))
        print("  most hammy tokens: ", ", ".join(f"{t}({w:+.2f})" for t, w in hammy[:8]))

    if len(chosen) > 1:
        print("\nsummary (accuracy / precision / recall / F1):")
        for key in chosen:
            a, p, r, f = metrics(*confusion(trained[key], test))
            print(f"  {key:7} {a*100:6.2f}  {p*100:6.2f}  {r*100:6.2f}  {f*100:6.2f}")
        print(f"\nReminder: a 'dumb' classifier that always says ham scores "
              f"{(1-base)*100:.1f}% accuracy. Accuracy alone is not the story -- "
              f"precision and recall are.")


if __name__ == "__main__":
    main()
