#!/usr/bin/env python3
"""
spam_torch.py  --  the same spam lab, in PyTorch.

Trains linear regression, logistic regression, and a small neural network on
the SMS Spam Collection using PyTorch, on whatever accelerator your machine
has: Apple-Silicon GPU (MPS), NVIDIA (CUDA), or CPU. The bag-of-words
featurizer is shared with the pure-Python version (spam_lab.py), so you can
compare the two implementations line for line.

Setup (MacBook Pro)
-------------------
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install torch
    python spam_torch.py

On Apple Silicon (M1/M2/M3/M4) that pip wheel is MPS-enabled and this script
will train on the GPU automatically. On an Intel Mac it trains on the CPU.
Force a device with --device {mps,cpu,cuda}.

Usage
-----
    python spam_torch.py                       # all three models
    python spam_torch.py --model logreg
    python spam_torch.py --classify "Free entry! Txt WIN to 80086"
    python spam_torch.py --epochs 30 --hidden 32 --device cpu
"""

import argparse
import sys

try:
    import torch
    import torch.nn as nn
except ImportError:
    sys.exit(
        "PyTorch is not installed. From this folder:\n"
        "    python3 -m venv .venv && source .venv/bin/activate\n"
        "    pip install -U pip && pip install torch\n"
        "Then re-run:  python spam_torch.py\n"
        "(No GPU needed -- it falls back to CPU. The zero-dependency version is "
        "spam_lab.py.)"
    )

# Reuse the data loader, split, tokenizer, and vocabulary from the stdlib lab.
import spam_lab as base


def pick_device(requested):
    if requested:
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def build_matrix(rows, vocab, device):
    """Dense bag-of-words matrix X (N x V) and label column y (N x 1)."""
    n, v = len(rows), len(vocab)
    X = torch.zeros(n, v, dtype=torch.float32)
    y = torch.zeros(n, 1, dtype=torch.float32)
    for r, (label, text) in enumerate(rows):
        for j, c in base.featurize(text, vocab).items():
            X[r, j] = float(c)
        y[r, 0] = float(label)
    return X.to(device), y.to(device)


# --------------------------------------------------------------------------
# Models -- each is a single nn.Module; the only differences are the last
# nonlinearity and the loss, exactly as in the lecture.
# --------------------------------------------------------------------------
def make_model(kind, dim, hidden):
    if kind == "linear":
        return nn.Linear(dim, 1)                       # score, MSE loss
    if kind == "logreg":
        return nn.Linear(dim, 1)                       # logit, BCEWithLogits
    if kind == "mlp":
        return nn.Sequential(
            nn.Linear(dim, hidden), nn.ReLU(), nn.Linear(hidden, 1)
        )
    raise ValueError(kind)


LOSSES = {
    "linear": nn.MSELoss(),                            # regression on {0,1}
    "logreg": nn.BCEWithLogitsLoss(),                  # sigmoid + cross-entropy
    "mlp": nn.BCEWithLogitsLoss(),
}
NAMES = {
    "linear": "linear regression (MSE)",
    "logreg": "logistic regression (BCE)",
    "mlp": "neural network (1 hidden layer)",
}


def proba(kind, model, X):
    """P(spam) for each row of X."""
    with torch.no_grad():
        out = model(X)
        if kind == "linear":
            return out.clamp(0, 1)                     # not a real probability
        return torch.sigmoid(out)


def train(kind, model, Xtr, ytr, device, epochs, lr, batch_size):
    model.to(device).train()
    loss_fn = LOSSES[kind]
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    n = Xtr.shape[0]
    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        total = 0.0
        for start in range(0, n, batch_size):
            idx = perm[start:start + batch_size]
            xb, yb = Xtr[idx], ytr[idx]
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            total += loss.item() * xb.shape[0]
        if epoch == 0 or (epoch + 1) % max(1, epochs // 5) == 0:
            print(f"    epoch {epoch+1:2d}/{epochs}  train loss {total/n:.4f}")
    model.eval()
    return model


# --------------------------------------------------------------------------
# Evaluation (mirrors spam_lab.py so the numbers are comparable)
# --------------------------------------------------------------------------
def evaluate(kind, model, X, y, rows, threshold=0.5, show=6):
    p = proba(kind, model, X).squeeze(1)
    pred = (p >= threshold).float()
    yv = y.squeeze(1)
    tp = int(((pred == 1) & (yv == 1)).sum())
    fp = int(((pred == 1) & (yv == 0)).sum())
    tn = int(((pred == 0) & (yv == 0)).sum())
    fn = int(((pred == 0) & (yv == 1)).sum())
    total = tp + fp + tn + fn
    acc = (tp + tn) / total
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print(f"  accuracy {acc*100:6.2f}%   precision {prec*100:6.2f}%   "
          f"recall {rec*100:6.2f}%   F1 {f1*100:6.2f}%")
    print(f"  confusion  TP={tp} FP={fp} TN={tn} FN={fn}")
    pl = p.tolist()
    print("  sample predictions:")
    for i in range(min(show, len(rows))):
        yt, text = rows[i]
        flag = "SPAM" if pl[i] >= 0.5 else "ham "
        print(f"    P(spam)={pl[i]:5.2f} -> {flag} | true={'spam' if yt else 'ham':4} | {text[:60]}")
    return acc, prec, rec, f1


def top_tokens(model, vocab, k=8):
    w = model.weight.detach().squeeze(0).tolist()   # nn.Linear weight (1 x V)
    inv = {i: t for t, i in vocab.items()}
    order = sorted(range(len(w)), key=lambda i: w[i])
    spammy = [(inv[i], w[i]) for i in order[::-1][:k]]
    hammy = [(inv[i], w[i]) for i in order[:k]]
    return spammy, hammy


def main():
    ap = argparse.ArgumentParser(description="Spam classification in PyTorch.")
    ap.add_argument("--data", default=base.DEFAULT_DATA)
    ap.add_argument("--model", choices=["linear", "logreg", "mlp", "all"], default="all")
    ap.add_argument("--max-features", type=int, default=2000)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--hidden", type=int, default=16)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", choices=["mps", "cpu", "cuda"], default=None)
    ap.add_argument("--classify", metavar="TEXT")
    args = ap.parse_args()

    torch.manual_seed(base.SEED)
    device = pick_device(args.device)
    print(f"PyTorch {torch.__version__} on device: {device}")

    rows = base.load(args.data)
    n_spam = sum(y for y, _ in rows)
    base_rate = n_spam / len(rows)
    print(f"Loaded {len(rows)} messages: {n_spam} spam / {len(rows)-n_spam} ham "
          f"(base rate {base_rate*100:.1f}%).")

    train_rows, test_rows = base.split(rows)
    vocab = base.build_vocab(train_rows, args.max_features)
    Xtr, ytr = build_matrix(train_rows, vocab, device)
    Xte, yte = build_matrix(test_rows, vocab, device)
    print(f"Vocabulary {len(vocab)} tokens.  Train {len(train_rows)} / test {len(test_rows)}.")

    if args.classify is not None:
        kind = "logreg" if args.model == "all" else args.model
        model = make_model(kind, len(vocab), args.hidden)
        train(kind, model, Xtr, ytr, device, args.epochs, args.lr, args.batch_size)
        x = build_matrix([(0, args.classify)], vocab, device)[0]
        p = float(proba(kind, model, x).squeeze())
        print(f"\n[{NAMES[kind]}]  P(spam) = {p:.3f}  ->  {'SPAM' if p >= 0.5 else 'ham'}")
        print(f"message: {args.classify!r}")
        return

    chosen = ["linear", "logreg", "mlp"] if args.model == "all" else [args.model]
    results = {}
    for kind in chosen:
        print(f"\n=== {NAMES[kind]} ===")
        model = make_model(kind, len(vocab), args.hidden)
        train(kind, model, Xtr, ytr, device, args.epochs, args.lr, args.batch_size)
        results[kind] = evaluate(kind, model, Xte, yte, test_rows)
        if kind == "logreg":
            spammy, hammy = top_tokens(model, vocab)
            print("  most spammy tokens:", ", ".join(f"{t}({w:+.2f})" for t, w in spammy))
            print("  most hammy tokens: ", ", ".join(f"{t}({w:+.2f})" for t, w in hammy))

    if len(chosen) > 1:
        print("\nsummary (accuracy / precision / recall / F1):")
        for kind in chosen:
            a, p, r, f = results[kind]
            print(f"  {kind:7} {a*100:6.2f}  {p*100:6.2f}  {r*100:6.2f}  {f*100:6.2f}")
        print(f"\nAlways-ham baseline: {(1-base_rate)*100:.1f}% accuracy. "
              f"Accuracy alone is not the story.")


if __name__ == "__main__":
    main()
