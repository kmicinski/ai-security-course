"""LLM backend: one OpenAI-compatible client, many places to point it.

Every backend we care about speaks the OpenAI chat-completions protocol:

  * Ollama on this machine            http://localhost:11434/v1
  * vLLM / Ollama on a rented GPU     https://<tunnel>.trycloudflare.com/v1
  * OpenRouter (pay-per-token)        https://openrouter.ai/api/v1
  * Groq / Together / Fireworks       (their /v1 endpoints)

So the demo is written once against that protocol, and a *profile* (see
PROFILES) just sets base_url / api_key / model.  `LLM_PROFILE` picks the
profile; any of `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` overrides it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

PROFILES: dict[str, dict[str, str]] = {
    # Free, local. Needs `ollama pull <model>`. Tool calling needs a model
    # that supports it (qwen2.5, qwen3, llama3.1+, mistral, gpt-oss).
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "qwen2.5:14b",
    },
    # Rented, per-token. Cheapest way to put a frontier-class open model
    # behind the demo. Set OPENROUTER_API_KEY. ~USD 0.1-0.9 per million tokens.
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "${OPENROUTER_API_KEY}",
        "model": "meta-llama/llama-3.3-70b-instruct",
    },
    # Groq: very fast hosted Llama; free tier is enough for one lecture.
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "${GROQ_API_KEY}",
        "model": "llama-3.3-70b-versatile",
    },
    # A GPU you rented yourself (Colab/RunPod) running vLLM or Ollama behind a
    # cloudflared tunnel. See colab/README.md. Set LLM_BASE_URL to the tunnel.
    "colab": {
        "base_url": "${LLM_BASE_URL}",
        "api_key": "${LLM_API_KEY:-none}",
        "model": "${LLM_MODEL:-Qwen/Qwen2.5-14B-Instruct-AWQ}",
    },
}


def _expand(v: str) -> str:
    """Expand ${VAR} and ${VAR:-default} in profile strings."""
    if not v.startswith("${"):
        return v
    inner = v[2:-1]
    if ":-" in inner:
        name, default = inner.split(":-", 1)
        return os.environ.get(name) or default
    return os.environ.get(inner, "")


@dataclass
class LLMConfig:
    profile: str
    base_url: str
    api_key: str
    model: str
    extra_body: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        profile = os.environ.get("LLM_PROFILE", "ollama")
        p = PROFILES.get(profile, PROFILES["ollama"])
        base_url = os.environ.get("LLM_BASE_URL") or _expand(p["base_url"])
        api_key = os.environ.get("LLM_API_KEY") or _expand(p["api_key"]) or "none"
        model = os.environ.get("LLM_MODEL") or _expand(p["model"])
        extra: dict[str, Any] = {}
        if profile == "openrouter":
            extra["provider"] = {"require_parameters": True}  # need tool support
        return cls(profile, base_url, api_key, model, extra)

    def public(self) -> dict[str, Any]:
        return {"profile": self.profile, "base_url": self.base_url, "model": self.model,
                "api_key_set": bool(self.api_key and self.api_key not in ("none", ""))}


class LLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=180)

    async def health(self) -> dict[str, Any]:
        try:
            models = await self.client.models.list()
            ids = [m.id for m in models.data]
            return {"ok": True, "models": ids[:50], "model_present": self.cfg.model in ids or not ids}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e), "models": []}

    async def stream_step(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int = 1200,
    ) -> AsyncIterator[dict[str, Any]]:
        """One model turn, streamed.

        Yields {"type": "token", "text"}, {"type": "reasoning", "text"} events as
        they arrive, then exactly one {"type": "done", "message": <assistant msg>,
        "tool_calls": [{id, name, arguments(dict)}]} event.  The assistant
        message is in OpenAI format, ready to append to `messages`.
        """
        kwargs: dict[str, Any] = dict(
            model=self.cfg.model, messages=messages, temperature=temperature,
            max_tokens=max_tokens, stream=True,
        )
        if tools:
            kwargs["tools"] = tools
        if self.cfg.extra_body:
            kwargs["extra_body"] = self.cfg.extra_body

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        # index -> {id, name, arguments(str)}; streamed tool calls arrive as deltas
        calls: dict[int, dict[str, str]] = {}

        stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            # Reasoning models (gpt-oss, deepseek-r1, qwen3) expose thinking via
            # a non-standard field; show it, it is pedagogically gold.
            r = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
            if r:
                reasoning_parts.append(r)
                yield {"type": "reasoning", "text": r}
            if delta.content:
                content_parts.append(delta.content)
                yield {"type": "token", "text": delta.content}
            for tc in delta.tool_calls or []:
                slot = calls.setdefault(tc.index or 0, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function.arguments:
                        slot["arguments"] += tc.function.arguments

        content = "".join(content_parts)
        tool_calls = []
        for i in sorted(calls):
            c = calls[i]
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {"_raw": c["arguments"]}
            tool_calls.append({"id": c["id"] or f"call_{i}", "name": c["name"], "arguments": args})

        msg: dict[str, Any] = {"role": "assistant", "content": content or None}
        if tool_calls:
            msg["tool_calls"] = [
                {"id": t["id"], "type": "function",
                 "function": {"name": t["name"], "arguments": json.dumps(t["arguments"])}}
                for t in tool_calls
            ]
        yield {"type": "done", "message": msg, "tool_calls": tool_calls,
               "reasoning": "".join(reasoning_parts)}

    async def classify(self, system: str, text: str, temperature: float = 0.0) -> str:
        """Single non-streamed call used by the LLM-judge defense."""
        resp = await self.client.chat.completions.create(
            model=self.cfg.model, temperature=temperature, max_tokens=200,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
            **({"extra_body": self.cfg.extra_body} if self.cfg.extra_body else {}),
        )
        return (resp.choices[0].message.content or "").strip()
