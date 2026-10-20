# Prompt Injection, Live — an interactive classroom demo

An interactive app that runs **real prompt-injection attacks against a real,
modern LLM** and shows, token by token, whether the attack worked. Built for
CIS400/600 Week 9–11 (LLM Security / Prompt Injection & Jailbreaking).

It is the running counterpart to the Week-11 deck: the same three attack
classes, the same five defenses, except here the class picks a payload, hits
**Run**, and watches the model either resist or get owned — including the tool
calls the agent makes and the moment a defense blocks (or fails to block) one.

```
┌────────────────┐     OpenAI-compatible /v1      ┌──────────────────────┐
│  FastAPI app   │ ────────────────────────────▶ │  an LLM you choose:   │
│  agent loop    │                                │  • Ollama (local Mac) │
│  + defenses    │ ◀──────────────────────────── │  • OpenRouter/Groq    │
│  + judge       │     tokens / tool calls         │  • your rented GPU    │
└────────────────┘                                └──────────────────────┘
        │  Server-Sent Events (live)
        ▼
   browser UI (Syracuse Orange/Navy)
```

Everything the "agent" touches — inboxes, web pages, an internal API, a shell —
is **simulated in memory**. No tool call leaves the machine. The offensive
payloads are here to be understood and defended against, in a sandbox, which is
the course's standing rule for offensive material.

## Quick start (local, free, on the Mac Studio)

```bash
# 1. a tool-calling model (one-time, ~9 GB)
ollama pull qwen2.5:14b          # 32b if you have the RAM; 7b/llama3.1:8b are lighter

# 2. run the app
cd demos/prompt-injection
cp .env.example .env             # default profile is already "ollama"
./run.sh                         # -> http://127.0.0.1:8008
```

Open the URL, pick a scenario, pick a payload, **Run attack**. The model badge
top-right turns green when the backend is reachable.

> The direct-injection scenario needs no tools and works with any chat model.
> The two agent scenarios need a model that supports **tool calling**
> (`qwen2.5`, `qwen3`, `llama3.1`+, `mistral`, `gpt-oss`). `deepseek-r1` is a
> reasoning model without reliable tool use — fine for scenario 1, not 2–3.

## Renting a better model (optional, cheap)

Three ways, cheapest effort first. Set them in `.env`:

1. **OpenRouter / Groq — per-token, no GPU to manage.** One API key, a
   frontier-class open model (Llama-3.3-70B, DeepSeek-V3) for cents per class.
   Uncomment the matching block in `.env` and drop in the key.
2. **A GPU you rent yourself (Colab/RunPod).** Open `colab/serve_llm_colab.ipynb`
   in Google Colab, set the runtime to GPU, run the cells. It serves Qwen2.5
   (14B/32B) with vLLM behind a public tunnel and prints the four `.env` lines
   to paste back. Colab Pro is ~USD 10/month.

Because every backend speaks the OpenAI chat protocol, the app code does not
change — only `.env`. See `app/llm.py` for the profile table.

## What's in the box

Three scenarios, matching the deck's taxonomy:

| # | Scenario | Class | What it teaches |
|---|----------|-------|-----------------|
| 1 | **Extract the system prompt** | Direct | The system prompt is not a security boundary; it is a trained preference you can argue with. |
| 2 | **Confused-deputy email agent** | Indirect | Untrusted *data* (an inbox message) becomes *instructions*; the agent acts with the user's authority. |
| 3 | **Browsing agent, URL exfiltration** | Indirect | A retrieved web page turns `fetch_url` into an exfiltration channel for a secret the agent holds. |

Five defenses you can toggle and watch succeed, then watch break:

- **Spotlighting / datamarking** — fence the untrusted span, tell the model it is data.
- **Sandwich** — restate the real task after the untrusted data.
- **Heuristic input filter** — a classifier scans and redacts (and so has a false-negative tail).
- **LLM judge** — a second model call screens untrusted text.
- **Tool-use policy** — a deterministic allowlist/confirm gate **outside the model**. The architectural fix; the throughline the course keeps returning to (control vs. data).

A **judge** inspects what actually happened (the tool calls and their effects,
not just the prose) and renders the verdict: *attacker won* or *attack blocked*,
with the concrete reason.

## Suggested classroom script (≈12 min)

1. **Scenario 1, "Ask nicely"** → model refuses. "Good, the preference holds."
2. **Scenario 1, "Ignore previous / translation / base64"** → one of them leaks
   the flag. "The boundary was never real."
3. **Scenario 2, undefended, "Direct exfiltration order"** → the agent sends the
   user's mail to the attacker. Point at the outbox in the verdict.
4. Turn on **spotlight**, re-run → often holds. Turn on **input filter** → holds
   for the obvious payload. Then run the **"fake tool protocol"** payload →
   it slips through. "A filter is a classifier; the attack optimizes against it."
5. Turn on **tool policy**, re-run the winning payload → **blocked**, and say
   why: the boundary moved *outside* the model. Tie back to complete mediation.
6. **Scenario 3** → show the secret leaving inside a URL, and the allowlist
   stopping it. Denominators, not vibes: let a few students try their own
   payloads in the editable box and count how many land.

## Files

```
app/
  server.py        FastAPI + the streaming agent loop + SSE
  llm.py           one OpenAI-compatible client; backend profiles
  defenses.py      the five defenses (content transforms + tool policy + judge)
  scenarios/       base.py + secret.py (direct) + email.py, web.py (indirect)
static/            single-page UI (index.html / app.css / app.js)
colab/             notebook to serve a bigger model from a rented GPU
run.sh  .env.example  pyproject.toml
```

## Notes / knobs

- **Temperature** slider: crank it to show injection is stochastic — re-run the
  same payload a few times and count the hits. That *is* the "verified success
  rate on a stated distribution" the course insists on.
- The app streams a reasoning model's hidden thoughts (`deepseek-r1`, `gpt-oss`,
  `qwen3`) when the backend exposes them — pedagogically useful for seeing the
  model talk itself into (or out of) compliance.
- `MAX_STEPS` in `server.py` caps the agent loop.
- This demo is intentionally **not** on the public course site by default; it is
  instructor infrastructure. Nothing here is added to `_data/release.yml`.
```
