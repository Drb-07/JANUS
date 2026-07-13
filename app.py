import streamlit as st
from fireworks.client import Fireworks
from google import genai
from google.genai import types
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
    provider: str = "Fireworks" # "Fireworks" or "Gemini"
    custom_api_key: Optional[str] = None
    model_name: str = "accounts/fireworks/models/llama-v3p1-70b-instruct"

# Default baseline squad setup
DEFAULT_ROSTER = {
    "tina_ui": AIAgent(
        id="tina_ui",
        name="Tina (UI/UX)",
        specialty="Frontend & Tailwind CSS",
        avatar="🎨",
        provider="Fireworks",
        system_prompt="You are Tina, a brilliant UI designer. You think visually and speak enthusiastically. You write clean Tailwind HTML layouts."
    ),
    "bob_backend": AIAgent(
        id="bob_backend",
        name="Bob (Backend)",
        specialty="Systems & APIs",
        avatar="⚙️",
        provider="Fireworks",
        system_prompt="You are Bob, a highly pragmatic backend engineer. You focus on data flow, logic, and scalability. You talk straight to the point."
    )
}

# ==========================================
# 2. PAGE SETUP & GLOBAL CONTEXT STATES
# ==========================================
st.set_page_config(page_title="DevSquad AI - Multi-Agent Forge", page_icon="🤖", layout="wide")
st.title("🤖 DevSquad AI Workspace (Hybrid Cloud)")
st.caption("Mix and match cross-provider agents (Fireworks AI & Google Gemini) in unified collaboration channels.")

if "api_key_verified" not in st.session_state:
    st.session_state.api_key_verified = False
if "fw_client" not in st.session_state:
    st.session_state.fw_client = None
if "gemini_global_key" not in st.session_state:
    st.session_state.gemini_global_key = None
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
    st.header("🔑 Workspace Keys")
    global_api_key = st.text_input("Default Fireworks Key:", type="password")
    if global_api_key:
        st.session_state.fw_client = Fireworks(api_key=global_api_key)
        st.session_state.api_key_verified = True
        
    global_gemini_key = st.text_input("Default Gemini API Key:", type="password")
    if global_gemini_key:
        st.session_state.gemini_global_key = global_gemini_key

    st.markdown("---")
    
    # --- Recruit Custom AI Agent ---
    st.header("➕ Recruit Custom AI Agent")
    with st.expander("Configure New Agent Profile", expanded=False):
        with st.form("agent_factory_form", clear_on_submit=True):
            new_name = st.text_input("Agent Name:")
            new_specialty = st.text_input("Description / Specialty:")
            new_avatar = st.text_input("Emoji Avatar:", value="🤖", max_chars=2)
            
            # Provider selector dropdown
            provider_choice = st.selectbox("AI Infrastructure Provider:", ["Fireworks", "Gemini"])
            
            # Automatically assign standard fast models based on choice
            default_model = "gemini-2.5-flash" if provider_choice == "Gemini" else "accounts/fireworks/models/llama-v3p1-70b-instruct"
            model_selection = st.text_input("Model Name/ID:", value=default_model)
            
            new_prompt = st.text_area("System Prompt Rules:")
            agent_specific_key = st.text_input("Dedicated API Key for this agent (Optional):", type="password")
            
            submit_agent = st.form_submit_button("Deploy Agent")
            
            if submit_agent and new_name and new_prompt:
                agent_id = new_name.lower().replace(" ", "_").strip()
                st.session_state.custom_roster[agent_id] = AIAgent(
                    id=agent_id,
                    name=new_name,
                    specialty=new_specialty,
                    avatar=new_avatar if new_avatar.strip() else "🤖",
                    provider=provider_choice,
                    model_name=model_selection,
                    system_prompt=new_prompt,
                    custom_api_key=agent_specific_key if agent_specific_key.strip() else None
                )
                st.success(f"{new_name} deployed via {provider_choice}!")
                st.rerun()

    st.markdown("---")
    
    # --- Live Active Roster Display ---
    st.header("🟢 AI Friends List")
    for agent_id, agent in st.session_state.custom_roster.items():
        st.markdown(f"{agent.avatar} **{agent.name}** — `{agent.provider}` ({agent.specialty})")
        
    st.markdown("---")
    
    # --- Group Workspace Controller ---
    st.header("💬 Group Chats")
    with st.form("create_group_form", clear_on_submit=True):
        new_group_name = st.text_input("Channel Name:")
        selected_agents = st.multiselect(
            "Invite Agents:",
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

# Render historic conversation logs
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
    
    # Run the conversational loop across the channel's roster
    for agent_key in active_agent_keys:
        if agent_key not in st.session_state.custom_roster:
            continue
        agent = st.session_state.custom_roster[agent_key]
        
        # 1. Resolve Credentials based on provider selection
        agent_key_to_use = agent.custom_api_key if agent.custom_api_key else (
            st.session_state.gemini_global_key if agent.provider == "Gemini" else global_api_key
        )
        
        if not agent_key_to_use:
            st.error(f"Skipping {agent.name}: Missing API Key for {agent.provider}.")
            continue
            
        # 2. Rebuild the string chat transcript history log for context
        context_history = ""
        for m in st.session_state.chats[current_channel][-12:]:
            context_history += f"[{m['sender']}]: {m['content']}\n\n"

        with st.chat_message("assistant", avatar=agent.avatar):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # --- ROUTE TO FIREWORKS ---
                if agent.provider == "Fireworks":
                    client = Fireworks(api_key=agent_key_to_use)
                    system_instruction = f"{agent.system_prompt}\nYou are inside channel '{current_channel}'."
                    payload = [{"role": "system", "content": system_instruction}, {"role": "user", "content": context_history}]
                    
                    response_stream = client.chat.completions.create(
                        model=agent.model_name, messages=payload, temperature=0.7, stream=True
                    )
                    for chunk in response_stream:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}▌")

                # --- ROUTE TO GEMINI ---
                elif agent.provider == "Gemini":
                    client = genai.Client(api_key=agent_key_to_use)
                    
                    # Gemini uses system_instruction parameter natively inside GenerateContentConfig
                    config = types.GenerateContentConfig(
                        system_instruction=f"{agent.system_prompt}\nYou are inside channel '{current_channel}'.",
                        temperature=0.7
                    )
                    
                    # Pass the whole transcript sequence directly to Gemini's input stream context
                    response_stream = client.models.generate_content_stream(
                        model=agent.model_name,
                        contents=f"Here is the discussion transcript so far. Continue the dialogue naturally as yourself:\n\n{context_history}",
                        config=config
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}▌")
                
                message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}")
                
            except Exception as e:
                st.error(f"Error executing agent {agent.name}: {str(e)}")
                continue
        
        # Save output to thread memory bank
        st.session_state.chats[current_channel].append({
            "role": "assistant",
            "sender": agent.name,
            "avatar": agent.avatar,
            "content": full_response
        })
