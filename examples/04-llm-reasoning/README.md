# LLMs, up close: tokens, next-token prediction, and the scratchpad

CIS400/600 demo. Downloads a small open-weights model (Qwen2.5-1.5B-Instruct,
~3 GB, no gated login), shows what the model actually consumes and emits, then
runs a controlled experiment on whether a "think step by step" scratchpad
improves accuracy — reported with denominators, not adjectives.

**Colab (the intended way to run this):** upload `llm_reasoning_demo.ipynb`, set
`Runtime → Change runtime type → Hardware accelerator: T4 GPU`, run all. It
carries its own source — nothing to clone, nothing but `transformers` to
install.

Sized for a **free** T4: the 1.5B weights are ~3.1 GB in fp16 against ~15 GB of
VRAM. About 3 minutes end to end for the default 30 tasks per condition, because
generation is batched (`BATCH_SIZE = 8`); one at a time it would be roughly 10.
Drop `BATCH_SIZE` to 4 on an OOM. CPU works but is several times slower — set
`N_PER_KIND = 3`.

The notebook calls `nvidia-smi` and `require_gpu()` up front, because Colab
hands out a CPU runtime silently if you forget to switch.

## What it teaches

| Part | Point |
| :-- | :-- |
| 2. Tokens | The model never sees characters. `13210` is several tokens; leading spaces belong to the token. Pairs with the tokenization slide in `slides/04-neural-networks-llm-intro`. |
| 2. Embeddings | A token id indexes a row of $E \in \mathbb{R}^{\|V\| \times d}$. |
| 2. Next token | One forward pass yields one distribution over the vocabulary. That is the whole output; temperature just rescales the logits. |
| 2. Greedy loop | `generate` written out: argmax, append, repeat. The append is the mechanism — what the model wrote becomes what the model reads. |
| 3. Chat template | The "conversation" is one flat string with delimiter tokens. Control and data share a channel. This is the setup for prompt injection. |
| 4. The experiment | Same model, same greedy decoding, same questions; only the system prompt differs. Accuracy per task family with n attached. |
| 5. Limits | The scratchpad can be fluent and wrong, post-hoc, or attacker-influenced. |

## The experiment

Two conditions — `direct` (must answer immediately) and `scratchpad` (may show
work, answer last) — over three generated task families with known-correct
answer keys: two-digit multiplication, multi-step word problems, and
last-letter concatenation. Greedy decoding in both, so no sampling noise sits
on top of the effect.

The notebook prints every disagreement in *both* directions, including tasks
where the scratchpad reasons its way to a wrong answer the direct condition got
right.

## Files

| Path | Role |
| :-- | :-- |
| `llm.py` | model loading, GPU checks, tokenization/embedding/logit inspection, chat (single and batched) |
| `tasks.py` | seeded task generator + answer key (stdlib only) |
| `prompts.py` | the two system prompts, answer extraction, grading (stdlib only) |
| `evaluate.py` | run both conditions, summarize with denominators |
| `notebook_cells.py` | notebook-only display and plots |
| `build_notebook.py` | generates the notebook from the files above |
| `verify.py` | checks the above without downloading the model |
| `llm_reasoning_demo.ipynb` | generated — do not hand-edit |

The modules are the source of truth. After changing one:

```bash
python3 build_notebook.py           # regenerate
python3 build_notebook.py --check   # fail if stale
```

## Checking a change

```bash
python3 verify.py     # stdlib only, no model download, ~1s
```

`verify.py` checks that the notebook matches its source and carries the inlined
definitions, that the task generator is deterministic and its answer key is
right (recomputed independently of `tasks.py`), that the grader accepts `4,233`
and the last of two `ANSWER:` lines but refuses `155 laptops`, and that the
harness scores a stub perfect model at 1.0 and a stub useless one at 0.0 with
denominators that add up.

Format failures are counted separately from wrong answers. A model that never
emits `ANSWER:` should show up as a broken format, not as a low score.

## Swapping the model

`llm.py` lists alternates. `Qwen2.5-0.5B-Instruct` widens the scratchpad gap;
`Qwen2.5-3B-Instruct` narrows it. Running at least two sizes is exercise 1 — the
effect size is a property of the model, not a constant.

Colab keeps one process for the whole session, so free the first model before
loading a second or the T4 runs out of memory:

```python
free(model)
tok, model = load("Qwen/Qwen2.5-3B-Instruct")   # ~6.2 GB in fp16, still fits
```
