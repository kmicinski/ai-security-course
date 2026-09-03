"""The two conditions under test, and the grader. Standard library only.

The whole experiment is one controlled comparison: identical model, identical
decoding, identical questions. The *only* thing that changes is whether the
prompt permits the model to write intermediate steps before committing to an
answer. Keep it that way -- if you also change temperature, or the answer
marker, or the number of examples, the comparison stops meaning anything.
"""

from __future__ import annotations

import re

# --8<-- start: prompts

ANSWER_MARKER = "ANSWER:"

# Condition A. No room to work: the answer marker is the first thing the model
# is allowed to emit, so every intermediate result has to be computed inside a
# single forward pass and carried in the activations.
DIRECT_SYSTEM = (
    "You are a careful assistant. Reply with exactly one line, in the form\n"
    f"{ANSWER_MARKER} <answer>\n"
    "Do not explain. Do not show any work. Do not write anything before the "
    f"{ANSWER_MARKER} line."
)

# Condition B. The scratchpad. The model may spend tokens computing, and those
# tokens are fed back in as context for the tokens that follow -- so the
# intermediate results live in the *input*, not in the activations.
SCRATCHPAD_SYSTEM = (
    "You are a careful assistant. Work the problem out step by step, showing "
    "each intermediate result on its own line. Keep it short.\n"
    f"When you are done, write the final answer on a new last line, in the form\n"
    f"{ANSWER_MARKER} <answer>\n"
    f"The {ANSWER_MARKER} line must contain the answer alone, with no units, "
    "no commas, and no explanation."
)

CONDITIONS = {"direct": DIRECT_SYSTEM, "scratchpad": SCRATCHPAD_SYSTEM}


def build_messages(question: str, condition: str) -> list[dict]:
    """The chat messages for one task under one condition."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    return [
        {"role": "system", "content": CONDITIONS[condition]},
        {"role": "user", "content": question},
    ]


_NUMBER = re.compile(r"-?\d[\d,]*")


def extract_answer(text: str) -> str:
    """Pull the model's committed answer out of its raw completion.

    Grading generative output is where benchmark numbers quietly go wrong, so
    the rule here is deliberately narrow and stated up front:

      1. take the text after the LAST answer marker (a scratchpad may mention
         the word "answer" while thinking; the commitment is the final one),
      2. failing that, fall back to the last number in the text,
      3. normalize: strip whitespace, thousands separators, trailing period.

    A model that never emits the marker and never emits a number scores zero.
    That is a real failure to follow the format, not a grader bug -- report it
    separately rather than hiding it by grading more generously.
    """
    marker = text.rfind(ANSWER_MARKER)
    if marker != -1:
        tail = text[marker + len(ANSWER_MARKER):]
        candidate = tail.strip().splitlines()[0] if tail.strip() else ""
    else:
        numbers = _NUMBER.findall(text)
        candidate = numbers[-1] if numbers else ""
    return normalize(candidate)


def normalize(s: str) -> str:
    """Make two answers comparable without making unequal answers equal."""
    s = s.strip().strip("*` ").rstrip(".")
    s = s.replace(",", "").replace("$", "")
    return s.strip().lower()


def is_correct(predicted: str, truth: str) -> bool:
    p, t = normalize(predicted), normalize(truth)
    if p == t:
        return True
    try:  # 155 and 155.0 are the same answer; "155 laptops" is not
        return float(p) == float(t)
    except ValueError:
        return False


# --8<-- end: prompts
