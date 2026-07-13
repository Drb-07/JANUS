"""
engine.py
---------
The orchestration loop for AI-GC. This is the "server" that routes messages
between the human user and however many AI agents are sitting in the channel,
all powered by Fireworks AI's chat completions endpoint.

Design:
  * Every message (from the user OR an agent) is appended to a shared
    `messages` list in st.session_state, each entry shaped like:
        {"role": "user" | "agent" | "system",
         "name": "user" | "<AgentName>",
         "content": "..."}
  * When the user posts a message, we look for @mentions:
       - "@AgentName" -> that specific agent is asked to reply
       - if NO agent is mentioned at all, every agent in the room is asked to
         reply once (like a normal group chat where everyone chimes in)
  * Agents can @mention each other (or @user) in their own reply. We chain up
    to MAX_CHAIN_DEPTH additional turns so agents can genuinely talk to each
    other, without letting the conversation run away forever.
  * Each agent only sees the shared transcript, formatted as a single
    Fireworks chat completion request:
        system: <that agent's persona>
        user:   <the rendered transcript up to now>
  * Network calls go straight to the Fireworks AI API using each agent's own
    api_key + model, so a group can genuinely be made of agents from
    different Fireworks accounts / model families.
"""

from __future__ import annotations

import requests
from typing import Optional

from src.agents import Agent, find_mentions, mentions_user

FIREWORKS_CHAT_URL = "https://api.fireworks.ai/inference/v1/chat/completions"

MAX_CHAIN_DEPTH = 4          # how many extra agent-to-agent hops we allow per user turn
REQUEST_TIMEOUT = 60


class FireworksError(RuntimeError):
    """Raised when the Fireworks API call fails or returns something unusable."""


def _render_transcript(messages: list[dict], limit: int = 40) -> str:
    """Turn the shared message log into a single readable transcript block."""
    lines = []
    for m in messages[-limit:]:
        speaker = "User" if m["role"] == "user" else m["name"]
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


def call_fireworks(agent: Agent, messages: list[dict]) -> str:
    """
    Send the rendered transcript to Fireworks AI as `agent`, using their own
    model + api_key, and return the text of their reply.
    """
    transcript = _render_transcript(messages)

    payload = {
        "model": agent.model,
        "max_tokens": agent.max_tokens,
        "temperature": agent.temperature,
        "messages": [
            {"role": "system", "content": agent.system_prompt()},
            {
                "role": "user",
                "content": (
                    "Here is the group chat so far. Reply as yourself, in your own "
                    "voice, with a single chat message (no need to restate your name). "
                    "You can @mention other members (including @user or other agents' "
                    "names) if you're addressing them directly.\n\n"
                    f"--- transcript ---\n{transcript}\n--- end transcript ---\n\n"
                    f"Now write {agent.name}'s next message:"
                ),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {agent.api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            FIREWORKS_CHAT_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as e:
        raise FireworksError(f"Network error calling Fireworks for {agent.name}: {e}") from e

    if resp.status_code != 200:
        raise FireworksError(
            f"Fireworks API error for {agent.name} ({resp.status_code}): {resp.text[:300]}"
        )

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as e:
        raise FireworksError(f"Unexpected Fireworks response for {agent.name}: {e}") from e


def route_user_message(
    user_text: str,
    agents: list[Agent],
    messages: list[dict],
) -> list[dict]:
    """
    Main entrypoint called by app.py whenever the human posts a message.

    Appends the user's message, figures out who should respond, calls
    Fireworks for each responder in turn (feeding each new reply back into
    the transcript so later agents see earlier agents' replies), and chains
    agent-to-agent @mentions up to MAX_CHAIN_DEPTH.

    Returns the list of newly-created message dicts (not including the
    original user message), in the order they were generated, each with an
    added "error" key (None on success) so the UI can flag failed calls
    without crashing the whole chat.
    """
    messages.append({"role": "user", "name": "user", "content": user_text})
    new_messages: list[dict] = []

    mentioned = find_mentions(user_text, agents)
    # Nobody explicitly @mentioned -> everyone in the room chimes in
    responders = mentioned if mentioned else list(agents)

    depth = 0
    queue = list(responders)
    already_replied_this_turn: set[str] = set()

    while queue and depth < MAX_CHAIN_DEPTH:
        agent = queue.pop(0)
        # avoid an agent replying to itself back-to-back in the same chain
        if agent.id in already_replied_this_turn:
            continue

        entry = {"role": "agent", "name": agent.name, "content": "", "error": None}
        try:
            reply = call_fireworks(agent, messages)
            entry["content"] = reply
        except FireworksError as e:
            entry["content"] = f"*(failed to respond: {e})*"
            entry["error"] = str(e)

        messages.append({"role": "agent", "name": agent.name, "content": entry["content"]})
        new_messages.append(entry)
        already_replied_this_turn.add(agent.id)
        depth += 1

        # did this agent tag other agents? queue them up for the next hop
        if entry["error"] is None:
            follow_ups = find_mentions(entry["content"], agents)
            for a in follow_ups:
                if a.id != agent.id and a.id not in already_replied_this_turn:
                    queue.append(a)

    return new_messages
