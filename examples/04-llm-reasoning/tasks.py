"""Deterministic task set for the reasoning demo. Standard library only.

Three families, chosen because they separate cleanly on whether a model is
allowed to write intermediate steps:

  arith   two-digit multiplication. One shot of pattern matching does badly;
          the partial-product decomposition is mechanical.
  words   multi-step word problems (GSM8K in miniature) built from templates,
          so the arithmetic is known-correct by construction.
  letters last-letter concatenation. No arithmetic at all, but the answer is a
          function of every input word, so a single forward pass has to carry
          all of them at once.

Everything here is generated from a seed rather than downloaded: the notebook
must run on Colab with no dataset dependency, and a grader that disagrees with
its own answer key is worse than no grader.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# --8<-- start: taskdef


@dataclass(frozen=True)
class Task:
    kind: str
    question: str
    answer: str  # the ground truth, already normalized


NAMES = ["Ana", "Ben", "Cleo", "Dmitri", "Esi", "Farid", "Gwen", "Hugo"]
ITEMS = ["batteries", "routers", "badges", "laptops", "sensors", "keycards"]
WORDS = [
    "packet", "router", "kernel", "buffer", "socket", "cipher", "daemon",
    "handle", "memory", "thread", "token", "vector", "matrix", "gradient",
]


def _arith(rng: random.Random) -> Task:
    a = rng.randint(12, 99)
    b = rng.randint(12, 99)
    return Task("arith", f"What is {a} * {b}?", str(a * b))


def _words(rng: random.Random) -> Task:
    name = rng.choice(NAMES)
    item = rng.choice(ITEMS)
    boxes = rng.randint(3, 9)
    per_box = rng.randint(6, 24)
    broken = rng.randint(2, 15)
    given = rng.randint(2, 12)
    total = boxes * per_box - broken - given
    q = (
        f"{name} has {boxes} boxes of {item}, with {per_box} in each box. "
        f"{broken} of the {item} are broken and thrown out, and {name} gives "
        f"{given} away. How many {item} does {name} have left?"
    )
    return Task("words", q, str(total))


def _letters(rng: random.Random) -> Task:
    picks = rng.sample(WORDS, 4)
    answer = "".join(w[-1] for w in picks)
    q = (
        "Take the last letter of each word and concatenate them, in order: "
        + ", ".join(picks)
        + "."
    )
    return Task("letters", q, answer)


BUILDERS = {"arith": _arith, "words": _words, "letters": _letters}


def make_tasks(n_per_kind: int = 10, seed: int = 400) -> list[Task]:
    """Return n_per_kind tasks of each family, in a fixed, reproducible order."""
    rng = random.Random(seed)
    out: list[Task] = []
    for kind in ("arith", "words", "letters"):
        seen: set[str] = set()
        while len([t for t in out if t.kind == kind]) < n_per_kind:
            task = BUILDERS[kind](rng)
            if task.question in seen:  # avoid duplicate draws inflating a score
                continue
            seen.add(task.question)
            out.append(task)
    return out


# --8<-- end: taskdef
