import streamlit as st
import os
from google import genai
from google.genai import types
# For Fireworks AI, we use the standard openai library protocol
from openai import OpenAI

st.set_page_config(page_title="Multi-Agent Chatroom", layout="wide")

# 1. INITIALIZE SYSTEM STATE MEMORY
if "agents" not in st.session_state:
    st.session_state.agents = {}
if "groups" not in st.session_state:
    st.session_state.groups = {}
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}
if "active_group" not in st.session_state:
    st.session_state.active_group = None

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("🤖 Orchestration Control")
    st.markdown("---")
    
    # SECTION A: RECRUIT / REGISTER CUSTOM AI AGENT
    st.subheader("➕ Recruit Custom AI Agent")
    
    with st.form("agent_creation_form", clear_on_submit=True):
        agent_name = st.text_input("Agent Name", placeholder="e.g., gemini, tech-expert")
        
        # Provider selection with Fireworks on top by default
        provider = st.selectbox("AI Provider Platform", ["Fireworks AI", "Gemini"])
        api_key = st.text_input("Provider API Key", type="password", placeholder="AIzaSy... or fw_...")
        
        system_prompt = st.text_area(
            "System Behavior Prompt", 
            value="You are a helpful AI assistant in a collaborative group chat environment."
        )
        
        submit_agent = st.form_submit_button("Deploy Agent to Roster")
        
        if submit_agent:
            if not agent_name or not api_key:
                st.error("❌ Both Agent Name and its corresponding API Key are strictly required.")
            else:
                # Add to memory roster
                st.session_state.agents[agent_name] = {
                    "name": agent_name,
                    "provider": provider,
                    "api_key": api_key,
                    "system_prompt": system_prompt
                }
                st.success(f"✔️ Registered agent '{agent_name}' via {provider}!")

    st.markdown("---")
    
    # SECTION B: CREATE A NEW GROUP CHAT
    st.subheader("💬 Establish Group Chat Room")
    with st.form("group_creation_form", clear_on_submit=True):
        group_name = st.text_input("Group Chat Name", placeholder="e.g., dev-team, main-room")
        
        # Select multiple agents registered in our system state
        available_agents = list(st.session_state.agents.keys())
        selected_agents = st.multiselect("Invite Agents to Room", options=available_agents)
        
        submit_group = st.form_submit_button("Launch Channel")
        
        if submit_group:
            if not group_name:
                st.error("❌ A unique group room name must be provided.")
            elif not selected_agents:
                st.error("❌ Invite at least one AI agent to make it a group chat.")
            else:
                st.session_state.groups[group_name] = selected_agents
                # Initialize empty message log for this specific room
                st.session_state.chat_histories[group_name] = []
                st.session_state.active_group = group_name
                st.success(f"🚀 Group channel '#{group_name}' launched!")

    st.markdown("---")
    
    # SECTION C: ACTIVE CHANNELS LIST
    st.subheader("📋 Available Channels")
    if st.session_state.groups:
        for g_name in st.session_state.groups.keys():
            # Bold highlight the active channel button
            label = f"💬 #{g_name}" if g_name != st.session_state.active_group else f"🔥 #{g_name} (Active)"
            if st.button(label, key=f"nav_{g_name}", use_container_width=True):
                st.session_state.active_group = g_name
                st.rerun()
    else:
        st.info("No active channels. Deploy an agent and launch a group chat room above.")

# --- MAIN CONVERSATION INTERFACE ---
st.title("⚡ Multi-Agent Collaborative Workbench")

if not st.session_state.active_group:
    st.info("👋 Welcome! Use the sidebar to add your AI agents and create a new group chat channel to begin.")
else:
    active_room = st.session_state.active_group
    invited_bots = st.session_state.groups[active_room]
    
    st.markdown(f"### Current Channel: `#{active_room}`")
    st.caption(f"**Active AI Cast Members inside this room:** {', '.join([f'`{b}`' for b in invited_bots])}")
    
    # 1. RENDER CURRENT CHAT HISTORY LOGS
    for msg in st.session_state.chat_histories[active_room]:
        with st.chat_message(msg["role"]):
            st.markdown(f"**{msg['author']}:** {msg['content']}")
            
    # 2. CAPTURE USER ENTRY INPUT WIDGET
    if user_prompt := st.chat_input(f"Send a message to #{active_room}..."):
        
        # Display and record user message immediately
        with st.chat_message("user"):
            st.markdown(f"**User:** {user_prompt}")
        st.session_state.chat_histories[active_room].append({
            "role": "user",
            "author": "User",
            "content": user_prompt
        })
        
        # Compile contextual string of the history log up to this point
        def build_history_context(history_list):
            context = ""
            for m in history_list:
                context += f"{m['author']}: {m['content']}\n"
            return context

        # 3. CASCADE LOOP EXECUTION FOR ACTIVE AGENTS IN THE ROOM
        for agent_id in invited_bots:
            agent = st.session_state.agents[agent_id]
            current_context = build_history_context(st.session_state.chat_histories[active_room])
            
            # Open up a dedicated rendering layout window block for the specific AI responder
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown(f"🤖 *{agent['name']} is synthesizing context...*")
                
                try:
                    # ROUTE TO GOOGLE GENAI SERVERS
                    if agent["provider"] == "Gemini":
                        client = genai.Client(api_key=agent["api_key"])
                        config = types.GenerateContentConfig(
                            system_instruction=agent["system_prompt"],
                            temperature=0.7
                        )
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=current_context,
                            config=config
                        )
                        ai_reply = response.text
                    
                    # ROUTE TO FIREWORKS AI SERVERS
                    elif agent["provider"] == "Fireworks AI":
                        # Fireworks adheres to standard OpenAI API construction
                        client = OpenAI(
                            base_url="https://api.fireworks.ai/inference/v1",
                            api_key=agent["api_key"]
                        )
                        response = client.chat.completions.create(
                            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
                            messages=[
                                {"role": "system", "content": agent["system_prompt"]},
                                {"role": "user", "content": current_context}
                            ],
                            temperature=0.7
                        )
                        ai_reply = response.choices[0].message.content
                        
                except Exception as e:
                    ai_reply = f"⚠️ Connection operational error via {agent['provider']}: {str(e)}"
                
                # Render the resulting string cleanly on screen
                message_placeholder.markdown(f"**{agent['name']}:** {ai_reply}")
                
            # Permanently record the text into history before looping onto the next bot
            st.session_state.chat_histories[active_room].append({
                "role": "assistant",
                "author": agent["name"],
                "content": ai_reply
            })
