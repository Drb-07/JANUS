"""
agents.py
---------
Defines the Agent data model and persona helpers for AI-GC (AI Group Chat).

An Agent is a friend you invite into your server. Each one has:
  - name:        Display name, used for @mentions (e.g. "@Nova")
  - model:       Fireworks AI model id ("link" the user provides, e.g.
                 "accounts/fireworks/models/llama-v3p1-70b-instruct")
  - api_key:     Fireworks API key used to authenticate calls made *as* this agent
                 (lets different agents run on different Fireworks accounts/keys
                 if the user wants, or all share one key)
  - persona:     System prompt describing who this agent is / how it behaves
  - color:       A hex accent color for their chat bubble / avatar ring
  - avatar:      A single emoji or letter used as their avatar glyph

Agents are stored in st.session_state so they persist for the browser session.
Nothing is written to disk -- API keys never leave the running Streamlit process.
"""

from __future__ import annotations

import uuid
import dataclasses
from typing import Optional


DEFAULT_PERSONA_TEMPLATE = (
    "You are {name}, a helpful and distinct AI personality living inside a group "
    "chat called AI-GC (like Discord, but the server members are AI agents). "
    "Other members of this chat may be the human user (mentioned as @user) or "
    "other AI agents (each mentioned by their own @name). Stay in character, "
    "keep replies conversational and not overly long, and only respond to what's "
    "relevant to you. If you are not directly addressed and have nothing useful "
    "to add, it's fine to stay quiet."
)

# A handful of ready-made personas so users can spin up a "friend" in one click
PERSONA_PRESETS = {
    "The Strategist": "a sharp, big-picture thinker who breaks tasks into clear steps and pushes the group toward a decision.",
    "The Skeptic": "a critical thinker who pokes holes in ideas, asks 'but what about...', and stress-tests plans before they ship.",
    "The Coder": "a terse, pragmatic software engineer who answers in code-first snippets and explains just enough to be useful.",
    "The Researcher": "a curious fact-finder who loves citing reasoning, comparing options, and surfacing tradeoffs.",
    "The Hype Friend": "an upbeat, encouraging teammate who keeps morale high and cheers the group on.",
    "The Comedian": "a witty agent who can't resist a joke but still gets things done.",
}

AVATAR_COLORS = [
    "#F23F42", "#F0B232", "#23A55A", "#5865F2",
    "#EB459E", "#00A8FC", "#F47B67", "#949CF7",
]


@dataclasses.dataclass
class Agent:
    """A single AI friend invited into the group chat."""

    name: str
    model: str                       # Fireworks model id ("the link")
    api_key: str                     # Fireworks API key for this agent
    persona: str = ""
    avatar: str = "🤖"
    color: str = "#5865F2"
    temperature: float = 0.8
    max_tokens: int = 512
    id: str = dataclasses.field(default_factory=lambda: uuid.uuid4().hex[:8])

    def mention(self) -> str:
        """How this agent is @mentioned in chat."""
        return f"@{self.name}"

    def system_prompt(self) -> str:
        if self.persona.strip():
            return self.persona
        return DEFAULT_PERSONA_TEMPLATE.format(name=self.name)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def make_agent(
    name: str,
    model: str,
    api_key: str,
    persona: str = "",
    avatar: Optional[str] = None,
    color: Optional[str] = None,
) -> Agent:
    """Factory used by the UI when the user fills in the 'Add Agent' form."""
    name = name.strip().lstrip("@")
    if not name:
        raise ValueError("Agent name cannot be empty.")
    if not model.strip():
        raise ValueError("Agent needs a Fireworks model link/id.")
    if not api_key.strip():
        raise ValueError("Agent needs a Fireworks API key.")

    idx = abs(hash(name)) % len(AVATAR_COLORS)
    return Agent(
        name=name,
        model=model.strip(),
        api_key=api_key.strip(),
        persona=persona.strip(),
        avatar=avatar or name[0].upper(),
        color=color or AVATAR_COLORS[idx],
    )


def find_mentions(text: str, agents: list[Agent]) -> list[Agent]:
    """Return the sublist of agents whose @name appears in `text`."""
    lowered = text.lower()
    mentioned = [a for a in agents if f"@{a.name.lower()}" in lowered]
    return mentioned


def mentions_user(text: str) -> bool:
    return "@user" in text.lower()
