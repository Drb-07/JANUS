"""
AI-GC — AI Group Chat
======================
Discord, but every "friend" in the server is an AI agent powered by Fireworks AI.

Add agents with a name + a Fireworks model link + an API key, invite them into
the channel, then talk to them (and watch them talk to each other) using
@mentions, exactly like a Discord server.
"""

import streamlit as st

from src.agents import Agent, make_agent, PERSONA_PRESETS
from src.engine import route_user_message

st.set_page_config(
    page_title="AI-GC · AI Group Chat",
    page_icon="🎮",
    layout="wide",
)

# --------------------------------------------------------------------------
# Session state bootstrap
# --------------------------------------------------------------------------
if "agents" not in st.session_state:
    st.session_state.agents: list[Agent] = []

if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = [
        {
            "role": "system",
            "name": "system",
            "content": (
                "Welcome to AI-GC! Add your first agent from the sidebar, then "
                "say hi with @mentions to start the conversation."
            ),
        }
    ]

if "invited" not in st.session_state:
    # agents currently "in the channel" (invited); lets you keep agents
    # defined but not part of every chat
    st.session_state.invited: set[str] = set()


# --------------------------------------------------------------------------
# Minimal Discord-flavored CSS on top of the dark theme in .streamlit/config.toml
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .chat-bubble {
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
        max-width: 100%;
    }
    .chat-name {
        font-weight: 700;
        margin-right: 8px;
    }
    .chat-meta {
        color: #949BA4;
        font-size: 0.75rem;
    }
    .avatar {
        display: inline-block;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        text-align: center;
        line-height: 32px;
        font-weight: 700;
        color: white;
        margin-right: 8px;
    }
    .server-pill {
        background-color: #2B2D31;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def agent_by_name(name: str) -> Agent | None:
    for a in st.session_state.agents:
        if a.name == name:
            return a
    return None


# --------------------------------------------------------------------------
# Sidebar — server member list + "Add Agent" form
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎮 AI-GC")
    st.caption("Your AI friends group chat, powered by Fireworks AI")

    st.divider()
    st.markdown("### ➕ Add a new agent")

    with st.form("add_agent_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="e.g. Nova")
        model = st.text_input(
            "Fireworks model link / id",
            placeholder="accounts/fireworks/models/llama-v3p1-70b-instruct",
            help="Any Fireworks AI chat-completions model id.",
        )
        api_key = st.text_input(
            "Fireworks API key", type="password", placeholder="fw_..."
        )
        preset = st.selectbox(
            "Persona starting point (optional)",
            ["Custom"] + list(PERSONA_PRESETS.keys()),
        )
        persona_default = "" if preset == "Custom" else PERSONA_PRESETS[preset]
        persona = st.text_area(
            "Persona / system prompt",
            value=persona_default,
            placeholder="Describe who this agent is and how they should behave...",
            height=90,
        )
        submitted = st.form_submit_button("Add friend", use_container_width=True)

        if submitted:
            try:
                agent = make_agent(name, model, api_key, persona)
                if agent_by_name(agent.name):
                    st.error(f"An agent named '{agent.name}' already exists.")
                else:
                    st.session_state.agents.append(agent)
                    st.session_state.invited.add(agent.id)
                    st.success(f"{agent.name} added and invited to the channel!")
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.markdown("### 👥 Server members")

    if not st.session_state.agents:
        st.caption("No agents yet — add one above.")
    else:
        for a in st.session_state.agents:
            invited = a.id in st.session_state.invited
            cols = st.columns([1, 4, 2])
            with cols[0]:
                st.markdown(
                    f"<div class='avatar' style='background:{a.color}'>{a.avatar}</div>",
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(f"**@{a.name}**")
                st.caption(a.model)
            with cols[2]:
                if invited:
                    if st.button("Remove", key=f"kick_{a.id}"):
                        st.session_state.invited.discard(a.id)
                        st.rerun()
                else:
                    if st.button("Invite", key=f"invite_{a.id}"):
                        st.session_state.invited.add(a.id)
                        st.rerun()

    st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()


# --------------------------------------------------------------------------
# Main channel view
# --------------------------------------------------------------------------
active_agents = [a for a in st.session_state.agents if a.id in st.session_state.invited]

st.markdown("### #general")
mention_hint = "  ·  ".join(f"@{a.name}" for a in active_agents) or "no agents invited yet"
st.caption(f"Members in channel: @user  ·  {mention_hint}")

chat_container = st.container(height=520)
with chat_container:
    for m in st.session_state.messages:
        if m["role"] == "system":
            st.info(m["content"])
            continue

        if m["role"] == "user":
            avatar_html = "<div class='avatar' style='background:#5865F2'>🧑</div>"
            display_name = "You"
            bg = "#2B2D31"
        else:
            agent = agent_by_name(m["name"])
            color = agent.color if agent else "#5865F2"
            glyph = agent.avatar if agent else "🤖"
            avatar_html = f"<div class='avatar' style='background:{color}'>{glyph}</div>"
            display_name = m["name"]
            bg = "#383A40"

        st.markdown(
            f"""
            <div style="display:flex; align-items:flex-start;">
                {avatar_html}
                <div class="chat-bubble" style="background:{bg}; flex:1;">
                    <span class="chat-name">{display_name}</span>
                    <div>{m['content']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --------------------------------------------------------------------------
# Message input
# --------------------------------------------------------------------------
prompt = st.chat_input(
    "Message #general  (use @AgentName to tag a friend, or @user for yourself)"
)

if prompt:
    if not active_agents:
        st.session_state.messages.append({"role": "user", "name": "user", "content": prompt})
        st.session_state.messages.append(
            {
                "role": "system",
                "name": "system",
                "content": "No agents are currently invited to the channel — invite one from the sidebar first.",
            }
        )
        st.rerun()
    else:
        with st.spinner("Waiting for replies..."):
            route_user_message(prompt, active_agents, st.session_state.messages)
        st.rerun()
