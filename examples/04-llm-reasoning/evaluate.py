"""Run both conditions over the task set and report accuracy with denominators.

The course line on any claimed capability is: what is the success rate, on what
distribution of targets, out of how many trials? This file exists so the answer
to "does a scratchpad help" is a table with an n in it, not a vibe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prompts import build_messages, extract_answer, is_correct
from tasks import Task

# --8<-- start: evaluate


@dataclass
class Result:
    task: Task
    condition: str
    raw: str  # the model's full completion, kept for inspection
    predicted: str
    correct: bool
    completion_tokens: int
    seconds: float

    @property
    def followed_format(self) -> bool:
        return self.predicted != ""


def run_condition(tok, model, chat_fn, tasks: list[Task], condition: str,
                  max_new_tokens: int = 256, progress: bool = True) -> list[Result]:
    """Ask every task under one condition. `chat_fn` is llm.chat."""
    results: list[Result] = []
    for i, task in enumerate(tasks, 1):
        reply = chat_fn(tok, model, build_messages(task.question, condition),
                        max_new_tokens=max_new_tokens)
        predicted = extract_answer(reply.text)
        results.append(Result(
            task=task,
            condition=condition,
            raw=reply.text,
            predicted=predicted,
            correct=is_correct(predicted, task.answer),
            completion_tokens=reply.completion_tokens,
            seconds=reply.seconds,
        ))
        if progress:
            mark = "." if results[-1].correct else "x"
            print(mark, end="", flush=True)
            if i % 30 == 0:
                print()
    if progress:
        print()
    return results


def run_condition_batched(tok, model, chat_batch_fn, tasks: list[Task], condition: str,
                          max_new_tokens: int = 256, batch_size: int = 8) -> list[Result]:
    """Same experiment as `run_condition`, generating in batches on the GPU.

    Identical prompts, identical greedy decoding -- only the scheduling differs,
    so the accuracy numbers are comparable to the sequential path. The one
    caveat is `seconds`: it is wall-clock for the batch divided by the batch
    size, which is throughput per answer, not the latency of a single answer.
    """
    messages = [build_messages(t.question, condition) for t in tasks]
    replies = chat_batch_fn(tok, model, messages, max_new_tokens=max_new_tokens,
                            batch_size=batch_size)
    results = []
    for task, reply in zip(tasks, replies):
        predicted = extract_answer(reply.text)
        results.append(Result(
            task=task,
            condition=condition,
            raw=reply.text,
            predicted=predicted,
            correct=is_correct(predicted, task.answer),
            completion_tokens=reply.completion_tokens,
            seconds=reply.seconds,
        ))
    return results


@dataclass
class Summary:
    condition: str
    kind: str
    n: int
    n_correct: int
    n_malformed: int
    mean_tokens: float
    mean_seconds: float

    @property
    def accuracy(self) -> float:
        return self.n_correct / self.n if self.n else 0.0


def summarize(results: list[Result]) -> list[Summary]:
    """Per (condition, kind) accuracy, plus the overall row for each condition."""
    out: list[Summary] = []
    conditions = sorted({r.condition for r in results})
    kinds = sorted({r.task.kind for r in results})
    for condition in conditions:
        for kind in kinds + ["ALL"]:
            rows = [r for r in results
                    if r.condition == condition
                    and (kind == "ALL" or r.task.kind == kind)]
            if not rows:
                continue
            out.append(Summary(
                condition=condition,
                kind=kind,
                n=len(rows),
                n_correct=sum(r.correct for r in rows),
                n_malformed=sum(not r.followed_format for r in rows),
                mean_tokens=sum(r.completion_tokens for r in rows) / len(rows),
                mean_seconds=sum(r.seconds for r in rows) / len(rows),
            ))
    return out


def print_table(summaries: list[Summary]) -> None:
    head = f"{'condition':<12}{'task':<9}{'acc':>9}{'n':>5}{'bad fmt':>9}{'tok':>7}{'sec':>7}"
    print(head)
    print("-" * len(head))
    for s in summaries:
        acc = f"{s.n_correct}/{s.n} = {100 * s.accuracy:4.0f}%"
        print(f"{s.condition:<12}{s.kind:<9}{acc:>9}"
              f"{s.n:>5}{s.n_malformed:>9}{s.mean_tokens:>7.0f}{s.mean_seconds:>7.2f}")
        if s.kind == "ALL":
            print()


def disagreements(results: list[Result]) -> list[tuple[Task, Result, Result]]:
    """Tasks where the two conditions disagree -- the interesting rows.

    Includes the ones where the SCRATCHPAD is wrong and the direct answer was
    right. Those exist, and dropping them would be the same selective reporting
    the course spends the semester complaining about.
    """
    by_key: dict[str, dict[str, Result]] = {}
    for r in results:
        by_key.setdefault(r.task.question, {})[r.condition] = r
    out = []
    for _, pair in by_key.items():
        if len(pair) < 2:
            continue
        a, b = pair.get("direct"), pair.get("scratchpad")
        if a and b and a.correct != b.correct:
            out.append((a.task, a, b))
    return out


# --8<-- end: evaluate
