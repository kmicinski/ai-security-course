"""Notebook-only helpers: display and plotting. No algorithms live here."""

from __future__ import annotations

# --8<-- start: display


def show_example(results, index: int = 0) -> None:
    """Print one task under both conditions, side by side, in full."""
    question = results[index].task.question
    pair = [r for r in results if r.task.question == question]
    print("QUESTION:", question)
    print("TRUTH:   ", pair[0].task.answer)
    for r in sorted(pair, key=lambda r: r.condition):
        print("\n" + "=" * 70)
        print(f"[{r.condition}]  {'CORRECT' if r.correct else 'WRONG'}   "
              f"({r.completion_tokens} tokens, {r.seconds:.2f}s)")
        print("-" * 70)
        print(r.raw)
        print("-" * 70)
        print("extracted:", repr(r.predicted))


def plot_accuracy(summaries) -> None:
    """Grouped bars: accuracy per task family, one bar per condition.

    Every bar is labelled with its own numerator and denominator. A bar chart
    of rates with the counts hidden is how a 3-of-5 result gets sold as 60%.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    kinds = [k for k in ["arith", "words", "letters", "ALL"]
             if any(s.kind == k for s in summaries)]
    conditions = sorted({s.condition for s in summaries})
    width = 0.8 / len(conditions)
    x = np.arange(len(kinds))

    fig, ax = plt.subplots(figsize=(8, 4.2))
    for j, condition in enumerate(conditions):
        vals, labels = [], []
        for kind in kinds:
            s = next((s for s in summaries
                      if s.condition == condition and s.kind == kind), None)
            vals.append(100 * s.accuracy if s else 0)
            labels.append(f"{s.n_correct}/{s.n}" if s else "")
        pos = x + j * width - 0.4 + width / 2
        bars = ax.bar(pos, vals, width, label=condition)
        for bar, label in zip(bars, labels):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                    label, ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x, kinds)
    ax.set_ylabel("accuracy (%)")
    ax.set_ylim(0, 112)
    ax.set_title("Same model, same decoding, same questions — only the prompt differs")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.show()


def plot_cost(summaries) -> None:
    """What the accuracy costs, in generated tokens per answer."""
    import matplotlib.pyplot as plt
    import numpy as np

    overall = [s for s in summaries if s.kind == "ALL"]
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    names = [s.condition for s in overall]
    ax.bar(names, [s.mean_tokens for s in overall], width=0.5)
    for i, s in enumerate(overall):
        ax.text(i, s.mean_tokens + 1, f"{s.mean_tokens:.0f} tok\n{s.mean_seconds:.2f}s",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("mean completion tokens")
    ax.set_title("Reasoning is not free")
    ax.set_ylim(0, max(s.mean_tokens for s in overall) * 1.35)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.show()


# --8<-- end: display
