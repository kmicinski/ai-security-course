# Information flow: does this program leak?

An in-class challenge app for **CIS400/600 lecture 2**. Eight small programs;
for each one the student decides what a public observer learns, then the app
runs the program over its **entire** secret input space and shows the answer
next to Denning's type checker.

The point of the app is the gap between those two things. It is small enough to
state in one line:

> A label checker is **sound but imprecise** for a batch observer, and **not even
> sound** for a stream or timing observer.

Every challenge is an instance of one side of that sentence.

## Running it

Any static server; ES modules will not load over `file://`.

```bash
python3 -m http.server 4010      # from this directory
open http://localhost:4010/
```

Keyboard: `1`–`4` pick an answer, `Enter` submits, `←` / `→` step through the
programs (and roll over into the next mode).

## The three modes

| Mode | Observer | Formally |
| :-- | :-- | :-- |
| **Batch** | reads the finished output, and only if the program terminates | `O_batch(r) = ⊥` if `r` diverges, else the output sequence |
| **Streams** | watches the pipe: each value as it is emitted, and the silence afterwards | `O_stream(r) = (output sequence, halted?)` |
| **Timing** | the stream observer plus a stopwatch | `O_time(r) = ((vᵢ, τᵢ)ᵢ, total time)` |

`O_batch ⊑ O_stream ⊑ O_time`: each observation is a function of the next, so
leakage is monotone along the chain. Any gap between two bars in the Leakage tab
is a channel the weaker observer cannot see. Students can switch the observer on
any program and watch the equivalence classes merge and split — the observer is
part of the threat model, and it is the part people forget to write down.

## The programs

| | Program | Checker | Batch | Stream | Timing | The point |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| `a1` | laundering through arithmetic | reject | 2 | 2 | 2 | joins propagate; algebra does not launder labels |
| `a2` | implicit flow, constants only | reject | 1 | 1 | 1 | the pc-label; copies vs. influence |
| `a3` | **tricky** — two outputs under one branch | reject ×4 | 1 | 1 | 1 | 4 rejections, 1 leaked bit, 1 harmless output: a label is a verdict, leakage is a number |
| `b1` | the stream that stops | **accept** | 0 | 2 | 2 | termination-insensitive soundness is all you get |
| `b2` | binary search over a secret | reject | 4 | 4 | 4 | gradual release, drawn as a staircase |
| `b3` | same multiset, different order | reject | 1 | 1 | 1 | ordering is a channel |
| `c1` | label-clean, clock-dirty | **accept** | 0 | 0 | 2 | the lattice model never mentions a clock |
| `c2` | early-exit PIN check | reject ×1 | 1 | 1 | 2 | the declassifier releases 1 bit; the clock releases more |

Bits are min-entropy leakage. `c2` is the one to slow down on: Shannon leakage
is 0.116 bits and min-entropy leakage is 1 bit for the same value channel, which
is the cleanest available argument for why you quote min-entropy when the threat
is guessing. Its timing channel turns a 32-guess average search into **12
guesses, worst case** — and the same argument turns a naive 16-byte MAC
comparison from 2¹²⁸ into 4096.

`a3` is the intended trap: students who have just seen "the checker is
incomplete" answer 0, and students who trust the checker answer 2. It is 1.

## Interactive parts worth using live

- **Observer toggle** (Runs / Leakage tabs) — same program, three threat models.
  On `b1` and `c1` the verdict flips as you click.
- **Public input control** on `c2` — the attacker picks the guess. Changing it
  moves the partition, which is exactly why the real attack has to be adaptive.
- **The fix** (`c1`, `c2`) — the defensive mirror. Loads the patched program into
  the bench and re-analyses it; the timing classes collapse.
- **Bench** — edit any program or its labels and re-run the whole analysis over
  the same input space. Paste in a student's proposed patch and see whether it
  actually closes the channel.

## The language

A tiny WHILE language with an output channel — assignment, `if`, `while`,
`out`, `skip`, integers, and one builtin `digit(x, i)`. Comments are `//`.

The **cost model** is stated on every program card and is deliberately
microarchitecture-free: one tick per statement step (assignment, `out`, `skip`,
and each `if`/`while` guard test), expression evaluation free. No caches, no
branch predictor, no memory hierarchy — a real clock leaks strictly more than
this one does. Divergence is detected by exhausting a step budget, not by
deciding halting; the ⊥ / "then silence…" rows stand for what a real observer
sees, namely no further output for as long as they have waited.

Noninterference is decided here by **enumerating** the declared finite high
domain. That is a decision procedure for these eight programs and nothing more.

## Files

| Path | Role |
| :-- | :-- |
| `js/lang.js` | lexer, parser, interpreter; the trace and the cost model |
| `js/checker.js` | Denning's flow constraints with a program-counter label |
| `js/analysis.js` | the three observers, partitioning, Shannon and min-entropy leakage |
| `js/challenges.js` | the eight programs, questions, and discussion |
| `js/app.js` | UI only — no analysis logic |
| `verify.mjs` | checks every stated expectation against the real implementation |

## After editing a program

`js/challenges.js` carries an `expect` block per challenge (checker verdict,
violation count, bits under each observer). It is not documentation — it is
tested:

```bash
node verify.mjs
```

The harness also enforces two invariants that must not break: the observer
hierarchy is monotone, and the checker never accepts a program that leaks to the
batch observer. Edit a program, re-run it, and fix the expectations from the
output rather than trusting the prose.
