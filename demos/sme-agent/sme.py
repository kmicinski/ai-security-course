"""Secure multi-execution (Devriese & Piessens, S&P 2010), two levels: L ⊑ H.

Run the program twice:

    L copy   real L inputs, ⊥ for every H input     performs only L outputs
    H copy   real L and H inputs                    performs only H outputs

Every L output comes from the L copy, and the L copy never saw an H input.
So nothing H can reach an L output, whatever the program does.
"""
from dataclasses import dataclass
from typing import Callable

L, H = "L", "H"
BOTTOM = "⊥"


@dataclass
class Tool:
    kind: str          # "in" or "out"
    label: str         # L or H
    run: Callable      # the real effect


class Copy:
    """The program's only handle on the world.  `enforce=False` is the unprotected run."""

    def __init__(self, level, tools, enforce=True):
        self.level, self.tools, self.enforce = level, tools, enforce
        self.log = []                       # (tool, args, what happened)

    def call(self, name, **args):
        t = self.tools[name]
        if t.kind == "in":
            if self.enforce and t.label == H and self.level == L:
                self.log.append((name, args, "⊥  (H input, L copy)"))
                return BOTTOM
            value = t.run(**args)
            self.log.append((name, args, f"→ {value!r}"))
            return value
        if self.enforce and t.label != self.level:
            self.log.append((name, args, f"DROPPED  ({t.label} output, {self.level} copy)"))
        else:
            t.run(**args)
            self.log.append((name, args, "SENT"))
        return "ok"                         # same answer either way


def run_unprotected(program, tools):
    c = Copy(H, tools, enforce=False)
    program(c)
    return {"agent": c.log}


def run_sme(program, tools):
    logs = {}
    for level in (L, H):                    # L first: L outputs never wait on H
        c = Copy(level, tools)
        program(c)
        logs[level] = c.log
    return logs
