"""Loading a small open-weights model and running text through it.

Everything the notebook does to the model goes through this file. The point of
keeping it separate is that none of it is magic: `generate` is a loop that
appends the argmax of a probability vector, and the chat "conversation" is one
flat string built by a template. Both are spelled out below so students can see
that, rather than taking a library's word for it.

Model: Qwen2.5-1.5B-Instruct. Chosen because the weights are openly downloadable
with no gated-repo login, it is ~3.1 GB in fp16 so it fits a free Colab T4 with
room to spare, and it is instruction-tuned well enough to follow an output
format -- which the experiment depends on.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# --8<-- start: load

DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# Smaller and larger alternates, if the default is too slow or too weak.
# 0.5B makes the scratchpad gap *bigger* (a weaker model needs the crutch more);
# 3B shrinks it. Both are worth trying -- the effect size is not a constant.
ALTERNATES = [
    "Qwen/Qwen2.5-0.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
]


def pick_device() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16  # T4 has fp16 tensor cores, not bf16
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32  # fp16 on CPU is slower, not faster


def require_gpu(strict: bool = False) -> bool:
    """Report the accelerator, and say plainly how to get one on Colab.

    Everything here runs on CPU, just slowly, so this warns by default rather
    than raising. Pass strict=True if you would rather stop than wait.
    """
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {name}  ({total:.1f} GB)")
        return True
    msg = ("No GPU. On Colab: Runtime -> Change runtime type -> Hardware "
           "accelerator: T4 GPU, then Runtime -> Restart session. "
           "Running on CPU works but is several times slower -- set "
           "N_PER_KIND = 3 below.")
    if strict:
        raise RuntimeError(msg)
    print("WARNING: " + msg)
    return False


def _from_pretrained(model_id: str, dtype):
    """`dtype=` on current transformers, `torch_dtype=` on older releases."""
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype)


def load(model_id: str = DEFAULT_MODEL):
    """Download (once) and return the tokenizer and model, on the best device."""
    device, dtype = pick_device()
    tok = AutoTokenizer.from_pretrained(model_id)
    # Batched generation needs a pad token and left padding (see chat_batch).
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = _from_pretrained(model_id, dtype)
    model.to(device)
    model.eval()
    print(f"{model_id} on {device} ({dtype})")
    print(f"parameters: {sum(p.numel() for p in model.parameters()) / 1e9:.2f} B")
    print(f"vocabulary: {len(tok)} tokens, embedding dim {model.config.hidden_size}")
    if device == "cuda":
        print(f"weights on GPU: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    return tok, model


def free(*objects) -> None:
    """Drop models and empty the CUDA cache, so you can load a second model.

    Colab keeps one Python process for the whole session; without this, loading
    3B after 1.5B can run the T4 out of memory.
    """
    import gc
    for o in objects:
        del o
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print(f"GPU memory now: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


# --8<-- end: load

# --8<-- start: inspect


def show_tokens(tok, text: str, limit: int = 24) -> list[int]:
    """Print how the tokenizer cuts `text` up, and return the ids.

    This is the deck's tokenization slide, made concrete: the model never sees
    the string. Note where the spaces go -- most tokens carry their leading
    space, which is why " cat" and "cat" are different tokens.
    """
    ids = tok.encode(text)
    pieces = [tok.decode([i]) for i in ids]
    print(f"{text!r}")
    print(f"  {len(ids)} tokens")
    for i, (tid, piece) in enumerate(zip(ids[:limit], pieces[:limit])):
        print(f"  [{i:>3}] {tid:>7}  {piece!r}")
    if len(ids) > limit:
        print(f"  ... {len(ids) - limit} more")
    return ids


def embedding_of(model, token_id: int) -> torch.Tensor:
    """The row of E that this token id selects. E is R^(|V| x d)."""
    return model.get_input_embeddings().weight[token_id]


@torch.no_grad()
def next_token_table(tok, model, text: str, k: int = 10, temperature: float = 1.0):
    """Top-k next-token distribution for a raw (already-templated) string.

    One forward pass, take the logits at the LAST position, softmax over the
    vocabulary. That vector is the entire model output -- everything else,
    including "reasoning", is this vector applied over and over.
    """
    device = next(model.parameters()).device
    inputs = tok(text, return_tensors="pt").to(device)
    logits = model(**inputs).logits[0, -1].float()
    probs = torch.softmax(logits / max(temperature, 1e-6), dim=-1)
    top = torch.topk(probs, k)
    return [(tok.decode([i]), float(p)) for p, i in zip(top.values, top.indices)]


@torch.no_grad()
def greedy_decode(tok, model, text: str, n_steps: int = 20) -> str:
    """`generate` with the lid off: argmax, append, repeat.

    Written out so the autoregressive loop is visible. Each new token is
    appended to the input, which is exactly why a scratchpad works at all --
    what the model wrote is now something the model can read.
    """
    device = next(model.parameters()).device
    ids = tok(text, return_tensors="pt").input_ids.to(device)
    for _ in range(n_steps):
        logits = model(input_ids=ids).logits[0, -1]
        nxt = int(torch.argmax(logits))
        if nxt == tok.eos_token_id:
            break
        ids = torch.cat([ids, torch.tensor([[nxt]], device=device)], dim=1)
    return tok.decode(ids[0], skip_special_tokens=True)


# --8<-- end: inspect

# --8<-- start: chat


@dataclass
class Reply:
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float


def render_prompt(tok, messages: list[dict]) -> str:
    """The flat string the model actually receives.

    Worth printing at least once in class. The "conversation" is not a data
    structure the model understands -- roles are delimiter tokens inside one
    string. Control and data share a channel, which is the whole reason prompt
    injection works, and is the same failure this course keeps returning to.
    """
    return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


@torch.no_grad()
def chat(tok, model, messages: list[dict], max_new_tokens: int = 256) -> Reply:
    """Greedy (deterministic) completion for a list of chat messages.

    do_sample=False on purpose: the experiment compares two prompts, and
    sampling noise would sit on top of the effect being measured.
    """
    device = next(model.parameters()).device
    prompt = render_prompt(tok, messages)
    inputs = tok(prompt, return_tensors="pt").to(device)
    start = time.perf_counter()
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tok.eos_token_id,
    )
    seconds = time.perf_counter() - start
    n_prompt = inputs["input_ids"].shape[1]
    new_ids = out[0][n_prompt:]
    return Reply(
        text=tok.decode(new_ids, skip_special_tokens=True).strip(),
        prompt_tokens=n_prompt,
        completion_tokens=int(new_ids.shape[0]),
        seconds=seconds,
    )


@torch.no_grad()
def chat_batch(tok, model, batch_messages: list[list[dict]],
               max_new_tokens: int = 256, batch_size: int = 8,
               progress: bool = True) -> list[Reply]:
    """Same as `chat`, but generates many prompts at once.

    This is the difference between a demo that finishes during class and one
    that does not. A GPU running one sequence at a time is almost entirely idle
    -- the weights have to be read from memory either way, so eight sequences
    cost barely more than one. On a T4 this is roughly a 5x speedup for the
    30-task run.

    Padding is on the LEFT. With right padding, the pads would sit between the
    prompt and the first generated token and the model would attend to them as
    if they were content.
    """
    device = next(model.parameters()).device
    prompts = [render_prompt(tok, m) for m in batch_messages]
    replies: list[Reply] = []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i:i + batch_size]
        enc = tok(chunk, return_tensors="pt", padding=True).to(device)
        start = time.perf_counter()
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tok.pad_token_id,
        )
        seconds = time.perf_counter() - start
        n_prompt = enc["input_ids"].shape[1]  # same for every row: left padded
        for row in range(len(chunk)):
            new_ids = out[row][n_prompt:]
            # After EOS the row is filled with pad; do not count that as work.
            kept = new_ids[new_ids != tok.pad_token_id]
            replies.append(Reply(
                text=tok.decode(new_ids, skip_special_tokens=True).strip(),
                prompt_tokens=n_prompt,
                completion_tokens=int(kept.shape[0]),
                seconds=seconds / len(chunk),  # wall clock, amortized
            ))
        if progress:
            print(f"  {len(replies)}/{len(prompts)}  ({seconds:.1f}s for {len(chunk)})",
                  flush=True)
    return replies


# --8<-- end: chat
