"""
AI-GC — AI Group Chat (URL Invocation Version)
==============================================
Discord, but every "friend" in the server is an AI agent powered by OpenRouter's
free chat models or direct Anthropic keys. 

Supports invoking agents instantly via URL link parameters.
"""

import streamlit as st
import json
import requests

from src.agents import (
    Agent,
    make_agent,
    PERSONA_PRESETS,
    FREE_MODEL_PRESETS,
    CLAUDE_MODEL_PRESETS_OPENROUTER,
    CLAUDE_MODEL_PRESETS_ANTHROPIC,
)
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
                "Welcome to AI-GC! Add an agent from the sidebar or via a share link, "
                "then say hi with @mentions to start the conversation."
            ),
        }
    ]

if "invited" not in st.session_state:
    st.session_state.invited: set[str] = set()


# --------------------------------------------------------------------------
# URL Query Parameter Handler (New Feature)
# --------------------------------------------------------------------------
# Check if someone shared a link containing a custom agent configuration
# Example: ?name=CyberMedic&persona=A+helpful+AI+doctor&model=google/gemma-2-9b-it:free&provider=openrouter
query_params = st.query_params

if "name" in query_params:
    url_name = query_params["name"].strip().lstrip("@")
    url_persona = query_params.get("persona", "").strip()
    url_model = query_params.get("model", "meta-llama/llama-3.1-8b-instruct:free").strip()
    url_provider = query_params.get("provider", "openrouter").strip()
    
    # Simple check to see if this agent is already configured in the session
    already_exists = any(a.name.lower() == url_name.lower() for a in st.session_state.agents)
    
    if not already_exists:
        st.info(f"✨ Found an invitation link for @{url_name}! Provide your API key in the sidebar to summon them.")
        # Store these parameters in temporary state to pre-populate the form
        st.session_state["preload_name"] = url_name
        st.session_state["preload_persona"] = url_persona
        st.session_state["preload_model"] = url_model
        st.session_state["preload_provider"] = url_provider


# --------------------------------------------------------------------------
# Minimal Discord-flavored CSS
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
    st.caption("Your AI friends group chat, powered by OpenRouter's free models")

    st.divider()
    st.markdown("### ➕ Add a new agent")

    # Read preloaded configurations if pulled from a shared URL link
    default_name = st.session_state.get("preload_name", "")
    default_persona = st.session_state.get("preload_persona", "")
    default_provider = st.session_state.get("preload_provider", "openrouter")
    default_model = st.session_state.get("preload_model", "")

    with st.form("add_agent_form", clear_on_submit=True):
        name = st.text_input("Name", value=default_name, placeholder="e.g. Nova")

        provider = st.radio(
            "Provider",
            ["openrouter", "anthropic"],
            index=0 if default_provider == "openrouter" else 1,
            format_func=lambda p: "OpenRouter (free models + Claude via credits)"
            if p == "openrouter"
            else "Anthropic directly (your own Claude API key)",
        )

        if provider == "openrouter":
            model_options = {**FREE_MODEL_PRESETS, **CLAUDE_MODEL_PRESETS_OPENROUTER}
            
            # Match the preset dropdown if the incoming link matches a known free model
            default_index = 0
            if default_model in model_options.values():
                default_index = list(model_options.values()).index(default_model) + 1
            elif default_model:
                default_index = 0 # Forces "Custom..." fallback

            model_choice = st.selectbox(
                "Model", 
                ["Custom..."] + list(model_options.keys()), 
                index=default_index
            )
            
            if model_choice == "Custom...":
                model = st.text_input(
                    "OpenRouter model link / id",
                    value=default_model,
                    placeholder="meta-llama/llama-3.1-8b-instruct:free",
                    help="Any OpenRouter chat-completions model id — browse free ones at openrouter.ai/models?max_price=0",
                )
            else:
                model = model_options[model_choice]
                st.caption(f"Model id: `{model}`")
                
            api_key = st.text_input(
                "OpenRouter API key",
                type="password",
                placeholder="sk-or-v1-...",
                help="Free at openrouter.ai — no credit card required for free models.",
            )
        else:
            model_choice = st.selectbox(
                "Claude model", list(CLAUDE_MODEL_PRESETS_ANTHROPIC.keys())
            )
            model = CLAUDE_MODEL_PRESETS_ANTHROPIC[model_choice]
            st.caption(f"Model id: `{model}`")
            api_key = st.text_input(
                "Anthropic API key",
                type="password",
                placeholder="sk-ant-...",
                help="From console.anthropic.com — this calls Claude directly.",
            )
            
        preset = st.selectbox(
            "Persona starting point (optional)",
            ["Custom"] + list(PERSONA_PRESETS.keys()),
        )
        persona_default = default_persona if default_persona else ("" if preset == "Custom" else PERSONA_PRESETS[preset])
        
        persona = st.text_area(
            "Persona / system prompt",
            value=persona_default,
            placeholder="Describe who this agent is and how they should behave...",
            height=90,
        )
        submitted = st.form_submit_button("Add friend", use_container_width=True)

        if submitted:
            try:
                agent = make_agent(name, model, api_key, provider=provider, persona=persona)
                if agent_by_name(agent.name):
                    st.error(f"An agent named '{agent.name}' already exists.")
                else:
                    st.session_state.agents.append(agent)
                    st.session_state.invited.add(agent.id)
                    st.success(f"{agent.name} added and invited to the channel!")
                    # Clear query state caches after adding successfully
                    st.query_params.clear()
                    for k in ["preload_name", "preload_persona", "preload_model", "preload_provider"]:
                        st.session_state.pop(k, None)
                    st.rerun()
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
                st.caption(f"{a.model}  ·  {a.provider}")
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
    "Message #general  (use @AgentName to tag a friend, or @user for yourself)",
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
