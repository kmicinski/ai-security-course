#!/usr/bin/env python3
"""Check the demo without downloading a 3 GB model.

    python3 verify.py

What it checks:

  * the notebook matches its source (build_notebook.py --check),
  * the notebook is valid JSON with the cell shape Colab expects,
  * the task generator is deterministic and its answer key is right --
    recomputed here independently of tasks.py,
  * the grader accepts what it should and refuses what it should not,
  * the evaluation harness scores a known-perfect and a known-useless model
    correctly, so a real run's numbers mean what the table says.

None of this needs torch: the parts that touch the model are exercised through
a stub `chat`. Running the model itself is the notebook's job, on a GPU.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evaluate  # noqa: E402
import prompts  # noqa: E402
import tasks  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAILURES.append(name)


def check_notebook() -> None:
    print("notebook")
    r = subprocess.run([sys.executable, str(HERE / "build_notebook.py"), "--check"],
                       capture_output=True, text=True)
    check("notebook matches its source", r.returncode == 0, r.stdout.strip())

    nb = json.loads((HERE / "llm_reasoning_demo.ipynb").read_text())
    check("nbformat 4", nb.get("nbformat") == 4)
    check("has cells", len(nb.get("cells", [])) > 20, f"{len(nb.get('cells', []))} cells")
    shapes_ok = all(
        c["cell_type"] in ("code", "markdown") and isinstance(c["source"], list)
        for c in nb["cells"])
    check("cell shapes are valid", shapes_ok)
    joined = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    for symbol in ("def load(", "def chat(", "def chat_batch(", "def require_gpu(",
                   "def free(", "def make_tasks(", "def extract_answer(",
                   "def run_condition(", "def run_condition_batched(",
                   "def plot_accuracy("):
        check(f"notebook inlines {symbol}...)", symbol in joined)
    check("notebook checks for a GPU", "nvidia-smi" in joined)
    check("notebook batches on the GPU", "run_condition_batched(tok" in joined)
    check("left padding is set at load time", 'padding_side = "left"' in joined)


def check_tasks() -> None:
    print("tasks")
    a = tasks.make_tasks(5, seed=400)
    b = tasks.make_tasks(5, seed=400)
    check("generation is deterministic", [t.question for t in a] == [t.question for t in b])
    check("seed changes the set",
          [t.question for t in a] != [t.question for t in tasks.make_tasks(5, seed=401)])
    check("15 tasks for n_per_kind=5", len(a) == 15)
    check("no duplicate questions", len({t.question for t in a}) == len(a))

    # Recompute the answer key independently of tasks.py.
    ok_arith = ok_letters = True
    for t in a:
        if t.kind == "arith":
            x, y = (int(n) for n in t.question.replace("?", "").split("is")[1].split("*"))
            ok_arith &= str(x * y) == t.answer
        if t.kind == "letters":
            words = t.question.split(":")[1].strip().rstrip(".").split(", ")
            ok_letters &= "".join(w[-1] for w in words) == t.answer
    check("arith answers are correct", ok_arith)
    check("letters answers are correct", ok_letters)


def check_grader() -> None:
    print("grader")
    cases = [
        ("ANSWER: 4233", "4233"),
        ("work work\nANSWER: 4,233", "4233"),
        ("ANSWER: 4233.", "4233"),
        ("no marker, the total is 4233", "4233"),    # fallback: last number
        ("ANSWER: 12\nwait, no\nANSWER: 15", "15"),  # the LAST commitment wins
        ("ANSWER: drnx", "drnx"),
        ("I refuse.", ""),                           # malformed, not wrong-answer
    ]
    for text, want in cases:
        got = prompts.extract_answer(text)
        check(f"extract {text.splitlines()[0][:28]!r}", got == want, f"-> {got!r}")
    check("155.0 == 155", prompts.is_correct("155.0", "155"))
    check("'155 laptops' != 155", not prompts.is_correct("155 laptops", "155"))
    check("empty is never correct", not prompts.is_correct("", "155"))


class StubReply:
    def __init__(self, text, n=7):
        self.text, self.completion_tokens, self.seconds = text, n, 0.01
        self.prompt_tokens = 42


def check_harness() -> None:
    print("harness")
    ts = tasks.make_tasks(4, seed=400)

    def oracle(tok, model, messages, max_new_tokens=256):
        question = messages[-1]["content"]
        truth = next(t.answer for t in ts if t.question == question)
        return StubReply(f"ANSWER: {truth}")

    def useless(tok, model, messages, max_new_tokens=256):
        return StubReply("ANSWER: 0")

    def mute(tok, model, messages, max_new_tokens=256):
        return StubReply("I would rather not.")

    perfect = evaluate.run_condition(None, None, oracle, ts, "direct", progress=False)
    check("a perfect model scores 1.0", all(r.correct for r in perfect))

    bad = evaluate.run_condition(None, None, useless, ts, "direct", progress=False)
    check("a useless model scores ~0", sum(r.correct for r in bad) == 0)

    silent = evaluate.run_condition(None, None, mute, ts, "direct", progress=False)
    check("format failures are counted, not graded as wrong-answer",
          all(not r.followed_format for r in silent))

    both = perfect + [evaluate.Result(task=r.task, condition="scratchpad", raw=r.raw,
                                      predicted="0", correct=False,
                                      completion_tokens=99, seconds=0.5)
                      for r in bad]
    summaries = evaluate.summarize(both)
    overall = {s.condition: s for s in summaries if s.kind == "ALL"}
    check("denominators add up", overall["direct"].n == len(ts))
    check("per-kind rows sum to ALL",
          sum(s.n for s in summaries if s.condition == "direct" and s.kind != "ALL")
          == overall["direct"].n)
    check("accuracy is a rate, not a count",
          overall["direct"].accuracy == 1.0 and overall["scratchpad"].accuracy == 0.0)
    check("disagreements finds every flipped task",
          len(evaluate.disagreements(both)) == len(ts))

    # The batched path must agree with the sequential one, answer for answer:
    # it changes scheduling only. If these ever diverge, suspect padding.
    def oracle_batch(tok, model, batch_messages, max_new_tokens=256, batch_size=8):
        return [StubReply(f"ANSWER: "
                          f"{next(t.answer for t in ts if t.question == m[-1]['content'])}")
                for m in batch_messages]

    batched = evaluate.run_condition_batched(None, None, oracle_batch, ts, "direct")
    check("batched path matches sequential, answer for answer",
          [r.predicted for r in batched] == [r.predicted for r in perfect])
    check("batched path preserves task order",
          [r.task.question for r in batched] == [t.question for t in ts])


def main() -> int:
    check_notebook()
    check_tasks()
    check_grader()
    check_harness()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
