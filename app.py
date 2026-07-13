import streamlit as st
from fireworks.client import Fireworks
from src.agents import AI_ROSTER

# 1. Page Configuration & Title
st.set_page_config(page_title="DevSquad AI - Multi-Agent Forge", page_icon="🤖", layout="wide")

st.title("🤖 DevSquad AI")
st.caption("Create group chats with specialized AI agents and watch them collaborate in real time.")

# Initialize global session states if they don't exist
if "api_key_verified" not in st.session_state:
    st.session_state.api_key_verified = False
if "chats" not in st.session_state:
    # Key: group_name, Value: list of message dicts
    st.session_state.chats = {"# general-brainstorm": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "# general-brainstorm"

# 2. Sidebar: Auth, Friends List, and Group Creation
with st.sidebar:
    st.header("🔑 Authentication")
    api_key = st.text_input("Enter Fireworks AI Key:", type="password")
    
    if api_key:
        st.session_state.fw_client = Fireworks(api_key=api_key)
        st.session_state.api_key_verified = True
        st.success("API Key Loaded!")
    else:
        st.warning("Please provide an API key to unlock the roster.")
        st.session_state.api_key_verified = False

    st.markdown("---")
    
    # AI Friends List Display
    st.header("🟢 AI Friends List")
    for agent_id, agent in AI_ROSTER.items():
        st.markdown(f"{agent.avatar} **{agent.name}** — *{agent.specialty}*")
        
    st.markdown("---")
    
    # Group Channels Section
    st.header("💬 Group Chats")
    
    # Form to create a new group chat
    with st.form("create_group_form", clear_on_submit=True):
        new_group_name = st.text_input("Group Name (e.g., #ui-revamp):")
        selected_agents = st.multiselect(
            "Invite Agents to Group:",
            options=list(AI_ROSTER.keys()),
            format_func=lambda x: f"{AI_ROSTER[x].avatar} {AI_ROSTER[x].name}"
        )
        submit_group = st.form_submit_button("Create Group")
        
        if submit_group and new_group_name:
            formatted_name = f"# {new_group_name.strip().replace(' ', '-').lower()}"
            if formatted_name not in st.session_state.chats:
                st.session_state.chats[formatted_name] = []
                # Store which agents belong to this specific group channel
                if "group_members" not in st.session_state:
                    st.session_state.group_members = {}
                st.session_state.group_members[formatted_name] = selected_agents
                st.session_state.current_chat = formatted_name
                st.rerun()

    # List out existing channels as clickable navigation buttons
    st.markdown("**Your Channels:**")
    for channel in st.session_state.chats.keys():
        if st.button(channel, use_container_width=True):
            st.session_state.current_chat = channel
            st.rerun()

# 3. Main Chat Interface Block
if not st.session_state.api_key_verified:
    st.info("← Please enter your Fireworks AI API Key in the sidebar to begin interacting with the squads.")
else:
    current_channel = st.session_state.current_chat
    st.subheader(f"Active Channel: {current_channel}")
    
    # Get active agents for the current room (default to all if general)
    active_agent_keys = st.session_state.group_members.get(current_channel, list(AI_ROSTER.keys())) \
        if "group_members" in st.session_state else list(AI_ROSTER.keys())

    # Display past conversation history
    for msg in st.session_state.chats[current_channel]:
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            st.markdown(f"**{msg['sender']}**\n\n{msg['content']}")

    # Handle New User Input
    if user_prompt := st.chat_input("Message the group..."):
        # Render and save User message
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"**You**\n\n{user_prompt}")
        
        st.session_state.chats[current_channel].append({
            "role": "user",
            "sender": "You",
            "avatar": "👤",
            "content": user_prompt
        })
        
        # Build shared group chat history for the context layer
        # Maps Streamlit architecture roles to standard LLM format
        context_history = []
        for m in st.session_state.chats[current_channel][-12:]: # Lookback window
            role = "user" if m["role"] == "user" else "assistant"
            context_history.append({"role": role, "content": f"[{m['sender']}]: {m['content']}"})

        # Agent Interaction Loop: Selected agents speak sequentially
        for agent_key in active_agent_keys:
            agent = AI_ROSTER[agent_key]
            
            # Create customized system context prompting them to react to the chat log
            system_instruction = (
                f"{agent.system_prompt}\n"
                f"You are inside the group chat channel '{current_channel}'. "
                f"Review the entire discussion transcript below. If your specialty is relevant, "
                f"reply directly to the user or bounce ideas off the other agents in the room."
            )
            
            messages_payload = [{"role": "system", "content": system_instruction}] + context_history

            # Call Fireworks AI using Llama 3.1 70B (Great compromise between smart orchestration and speed)
            with st.chat_message("assistant", avatar=agent.avatar):
                message_placeholder = st.empty()
                full_response = ""
                
                # Use Streaming so the user feels like the AI is active in live text typing mode
                response_stream = st.session_state.fw_client.chat.completions.create(
                    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
                    messages=messages_payload,
                    temperature=0.7,
                    stream=True
                )
                
                for chunk in response_stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}▌")
                
                message_placeholder.markdown(f"**{agent.name}**\n\n{full_response}")
            
            # Save this agent's response into the running history state
            st.session_state.chats[current_channel].append({
                "role": "assistant",
                "sender": agent.name,
                "avatar": agent.avatar,
                "content": full_response
            })
            
            # Update history block array so subsequent agents can read what *this* agent just said
            context_history.append({"role": "assistant", "content": f"[{agent.name}]: {full_response}"})
