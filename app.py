import streamlit as st
from fireworks.client import Fireworks
from src.agents import AI_ROSTER, AIAgent

# Initialize global states for tracking custom-added agents
if "custom_roster" not in st.session_state:
    # Seed with the baseline default team from your agents file
    st.session_state.custom_roster = AI_ROSTER.copy()

with st.sidebar:
    st.title("🔧 Forge Control Panel")
    
    # 1. Bring Your Own Key Portal
    api_key = st.text_input("Enter Fireworks AI Key:", type="password")
    if api_key:
        st.session_state.fw_client = Fireworks(api_key=api_key)
        st.session_state.api_key_verified = True
    else:
        st.session_state.api_key_verified = False

    st.markdown("---")
    
    # 2. Dynamic Agent Factory (Add New AI Section)
    st.header("➕ Add a New AI Agent")
    with st.expander("Configure New Agent Persona", expanded=False):
        with st.form("agent_factory_form", clear_on_submit=True):
            new_name = st.text_input("Agent Name (e.g., Dave Coder):")
            new_specialty = st.text_input("Specialty (e.g., Database Optimizer):")
            new_avatar = st.selectbox("Select Emoji Avatar:", ["💻", "🚀", "👁️", "✍️", "📊", "🧠", "🔥", "🛠️"])
            new_prompt = st.text_area(
                "System Prompt (Behavior Instructions):", 
                placeholder="Explain how this agent acts, their constraints, and formatting rules..."
            )
            submit_agent = st.form_submit_button("Deploy Agent to Roster")
            
            if submit_agent and new_name and new_prompt:
                # Format a unique internal dictionary key ID
                agent_id = new_name.lower().replace(" ", "_")
                
                # Append the new persona structure to the running session state roster
                st.session_state.custom_roster[agent_id] = AIAgent(
                    id=agent_id,
                    name=new_name,
                    specialty=new_specialty,
                    avatar=new_avatar,
                    system_prompt=new_prompt
                )
                st.success(f"{new_name} is now online!")
                st.rerun()

    st.markdown("---")
    
    # 3. Dynamic Roster List View
    st.header("🟢 AI Friends List")
    for agent_id, agent in st.session_state.custom_roster.items():
        st.markdown(f"{agent.avatar} **{agent.name}** — *{agent.specialty}*")
        
    st.markdown("---")
    
    # 4. Group Chats Management Channel Hub
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
                if "group_members" not in st.session_state:
                    st.session_state.group_members = {}
                # Tie the specific channel namespace to the selected agents group array
                st.session_state.group_members[formatted_name] = selected_agents
                st.session_state.current_chat = formatted_name
                st.rerun()

    st.markdown("**Active Channels:**")
    for channel in st.session_state.chats.keys():
        if st.button(channel, use_container_width=True):
            st.session_state.current_chat = channel
            st.rerun()
