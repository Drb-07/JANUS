import streamlit as st
from fireworks.client import Fireworks
from pydantic import BaseModel
from typing import Optional

# ==========================================
# 1. DATA MODELS & INLINE ROSTER DEFINITION
# ==========================================
class AIAgent(BaseModel):
    id: str
    name: str
    specialty: str
    avatar: str  
    system_prompt: str
    custom_api_key: Optional[str] = None
    model_name: str = "accounts/fireworks/models/llama-v3p1-70b-instruct"

# Default baseline squad setup
DEFAULT_ROSTER = {
    "tina_ui": AIAgent(
        id="tina_ui",
        name="Tina (UI/UX)",
        specialty="Frontend & Tailwind CSS",
        avatar="🎨",
        system_prompt="You are Tina, a brilliant UI designer. You think visually and speak enthusiastically. You write clean Tailwind HTML layouts. When someone asks you a question or hands you a backend plan, explain your UI approach and provide mockup concepts."
    ),
    "bob_backend": AIAgent(
        id="bob_backend",
        name="Bob (Backend)",
        specialty="Systems & APIs",
        avatar="⚙️",
        system_prompt="You are Bob, a highly pragmatic backend engineer. You focus on data flow, logic, and scalability. You talk straight to the point. When addressing the group, draft API endpoints, specify logic, or point out technical structural flaws."
    ),
    "quinn_qa": AIAgent(
        id="quinn_qa",
        name="Quinn (QA/Debugger)",
        specialty="Testing & Code Polish",
        avatar="🛡️",
        system_prompt="You are Quinn, a meticulous, skeptical QA engineer. Your job is to poke holes in Bob and Tina's plans. Look out for edge cases, security vulnerabilities, or logical bugs. Be constructive but critical."
    )
}

# ==========================================
# 2. PAGE SETUP & GLOBAL CONTEXT STATES
# ==========================================
st.set_page_config(
    page_title="DevSquad AI - Multi-Agent Forge", 
    page_icon="🤖", 
    layout="wide"
)

st.title("🤖 DevSquad AI Workspace")
st.caption("Recruit specialized AI agents with custom credentials, spin up group channels, and orchestrate real-time team collaboration loops.")

# Manage state allocations across Streamlit app execution cycles
if "api_key_verified" not in st.session_state:
    st.session_state.api_key_verified = False
if "fw_client" not in st.session_state:
    st.session_state.fw_client = None
if "custom_roster" not in st.session_state:
    st.session_state.custom_roster = DEFAULT_ROSTER.copy()
if "chats" not in st.session_state:
    st.session_state.chats = {"# general-brainstorm": []}
if "group_members" not in st.session_state:
    st.session_state.group_members = {"# general-brainstorm": list(DEFAULT_ROSTER.keys())}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "# general-brainstorm"

# ==========================================
# 3. CONTROL PANEL (SIDEBAR ENVIRONMENT)
# ==========================================
with st.sidebar:
    st.title("🔧 Forge Control Panel")
    
    # --- Framework Auth Portal ---
    st.header("🔑 Global Workspace Key")
    global_api_key = st.text_input(
        "Default Fireworks AI API Key:", 
        type="password", 
        help="Fallback key used if an agent doesn't have an individual credential assigned."
    )
    
    if global_api_key:
        st.session_state.fw_client = Fireworks(api_key=global_api_key)
        st.session_state.api_key_verified = True
    else:
        st.session_state.api_key_verified = False
        st.warning("Provide a global key or ensure all deployed agents use dedicated custom keys.")

    st.markdown("---")
    
    # --- Recruit Custom AI Agent ---
    st.header("➕ Recruit Custom AI Agent")
    with st.expander("Configure New Agent Profile", expanded=False):
        with st.form("agent_factory_form", clear_on_submit=True):
            new_name = st.text_input("Agent Name:", placeholder="e.g., CodeNinja")
            new_specialty = st.text_input("Description / Specialty:", placeholder="e.g., Python Backend Optimization")
            new_avatar = st.text_input("Emoji Avatar:", value="🤖", max_chars=2, help="Paste any visual emoji emblem")
            new_prompt = st.text_area(
                "System Prompt Rules:", 
                placeholder="Act as an expert... Write clean code blocks... Challenge bad logic..."
            )
            agent_specific_key = st.text_input(
                "Dedicated Fireworks API Key (Optional):", 
                type="password",
                help="Leave blank to drop back to using the global system workspace credentials."
            )
            
            submit_agent = st.form_submit_button("Deploy Agent to Roster")
            
            if submit_agent and new_name and new_prompt:
                agent_id = new_name.lower().replace(" ", "_").strip()
                
                st.session_state.custom_roster[agent_id] = AIAgent(
                    id=agent_id,
                    name=new_name,
                    specialty=new_specialty,
                    avatar=new_avatar if new_avatar.strip() else "🤖",
                    system_prompt=new_prompt,
                    custom_api_key=agent_specific_key if agent_specific_key.strip() else None
                )
                st.success(f"{new_name} has joined the roster!")
                st.rerun()

    st.markdown("---")
    
    # --- Live Active Roster Display ---
    st.header("🟢 AI Friends List")
    for agent_id, agent in st.session_state.custom_roster.items():
        key_badge = "🔑 Custom Key" if agent.custom_api_key else "🌐 Global Key"
        st.markdown(f"{agent.avatar} **{agent.name}** — *{agent.specialty}* `({key_badge})`")
        
    st.markdown("---")
    
    # --- Group Workspace Controller ---
    st.header("💬 Group Chats")
    with st.form("create_group_form", clear_on_submit=True):
        new_group_name = st.text_input("Channel Name (e.g., dev-sprint):")
        selected_agents = st.multiselect(
            "Invite Agents to Room:",
            options=list(st.session_state.custom_roster.keys()),
            format_func=lambda x: f"{st.session_state.custom_roster[x].avatar} {st.session_state.custom_roster[x].name}"
        )
        submit_group = st.form_submit_button("Launch Channel")
        
        if submit_group and new_group_name:
            formatted_name = f"# {new_group_name.strip().replace(' ', '-').lower()}"
            if formatted_name not in st.session_state.chats:
                st.session_state.chats[formatted_name] = []
                st.session_state.group_members[formatted_name] = selected_agents
                st.session_state.current_chat = formatted_name
                st.rerun()

    st.markdown("**Active Channels:**")
    for channel in st.session_state.chats.keys():
        if st.button(channel, use_container_width=True):
            st.session_state.current_chat = channel
            st.rerun()

# ==========================================
# 4. CONVERSATION INTERACTION PLANE
# ==========================================
current_channel = st.session_state.current_chat
st.subheader(f"Active Channel: {current_channel}")

active_agent_keys = st.session_state.group_members.get(current_channel, [])
has_global_key = st.session_state.api_key_verified
has_agent_with_custom_key = any(st.session_state.custom_roster[k].custom_api_key for k in active_agent_keys)

if not has_global_key and not has_agent_with_custom_key:
    st.info("← Provide a global Fireworks API key or configure an agent with a custom API credential to begin.")
else:
    for msg in st.session_state.chats[current_channel]:
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            st.markdown(f"**{msg['sender']}**\n\n{msg['content']}")

    if user_prompt := st.chat_input("Message the group room..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"**You**\n\n{user_prompt}")
        
        st.session_state.chats[current_channel].append({
            "role": "user",
            "sender": "You",
            "avatar": "👤",
            "content": user_prompt
        })
        
        context_history = []
        for m in st.session_state.chats[current_channel][-16:]:
            role = "user" if m["role"] == "user" else "assistant"
            context_history.append({"role": role, "content": f"[{m['sender']}]: {m['content']}"})

        for agent_key in active_agent_keys:
            if agent_key not in st.session_state.custom_roster:
                continue
            agent = st.session_state.custom_roster[agent_key]
            
            if agent.custom_api_key:
                current_client = Fireworks(api_key=agent.custom_api_key)
            elif st.session_state.fw_client:
                current_client = st.session_state.fw_client
            else:
                st.error(f"Skipping execution for {agent.name}: Lacks API credentials.")
                continue
                
            system_instruction = (
                f"{agent.system_prompt}\n"
                f"You are collaborating live inside a multi-agent team room channel named '{current_channel}'. "
                f"Analyze the structural flow of the discussion history log. If your engineering specialty "
                f"or analytical persona is relevant to the problem space, reply to the user or address other team "
                f"members directly by tagging them."
            )
            
            messages_payload = [{"role": "system", "content": system_instruction}] + context_history

            with st.chat_message("assistant", avatar=agent.avatar):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                    response_stream = current_client.chat.completions.create(
                        model=agent.model_name,
                        messages=messages_payload,
                        temperature=0.7,
                        stream=True
                    )
                    
                    for chunk in response_stream:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}▌")
                    
                    message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}")
                    
                except Exception as e:
                    st.error(f"Inference processing failure on agent network interface: {str(e)}")
                    continue
            
            st.session_state.chats[current_channel].append({
                "role": "assistant",
                "sender": agent.name,
                "avatar": agent.avatar,
                "content": full_response
            })
            context_history.append({"role": "assistant", "content": f"[{agent.name}]: {full_response}"})
