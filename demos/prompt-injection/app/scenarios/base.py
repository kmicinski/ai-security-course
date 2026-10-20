"""Scenario = a victim application + a place where attacker-controlled text
enters the model's context + a judge that says whether the attacker won.

Everything here is simulated: the "inbox", "web", "filesystem" and "shell" are
in-memory dictionaries. No tool ever touches the real machine or network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# A tool call the model made, plus what the environment answered.
@dataclass
class ToolEvent:
    name: str
    arguments: dict[str, Any]
    result: str
    blocked: bool = False       # a policy (allowlist) refused to execute it
    untrusted: bool = False     # the result carries attacker-controlled text


@dataclass
class Trace:
    """What happened in one episode. The judge reads this."""
    final_text: str = ""
    tool_events: list[ToolEvent] = field(default_factory=list)
    env: dict[str, Any] = field(default_factory=dict)

    def calls(self, name: str) -> list[ToolEvent]:
        return [t for t in self.tool_events if t.name == name and not t.blocked]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[[dict[str, Any], dict[str, Any]], str]   # (env, args) -> result text
    untrusted_result: bool = False   # result contains attacker-reachable content
    sensitive: bool = False          # side effect worth gating (send, exec, ...)

    def schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}


@dataclass
class Payload:
    name: str
    text: str
    note: str = ""


@dataclass
class Scenario:
    id: str
    title: str
    kind: str                    # "direct" (payload is the user turn) | "indirect" (payload is in data)
    blurb: str                   # one paragraph for the UI
    attacker_goal: str           # what "success" means, in words
    system_prompt: str
    user_prompt: str             # the *victim's* request (indirect) or a prefix (direct)
    payloads: list[Payload]
    tools: list[Tool] = field(default_factory=list)
    build_env: Callable[[str], dict[str, Any]] = lambda payload: {}
    judge: Callable[[Trace], tuple[bool, str]] = lambda t: (False, "no judge")
    # Tool-policy defense: return a refusal string to block, None to allow.
    policy: Callable[[str, dict[str, Any], dict[str, Any]], str | None] = lambda n, a, e: None
    injection_site: str = ""     # where the payload lands, for the UI

    def tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "kind": self.kind, "blurb": self.blurb,
            "attacker_goal": self.attacker_goal, "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt, "injection_site": self.injection_site,
            "payloads": [p.__dict__ for p in self.payloads],
            "tools": [{"name": t.name, "description": t.description,
                       "sensitive": t.sensitive, "untrusted": t.untrusted_result} for t in self.tools],
        }
