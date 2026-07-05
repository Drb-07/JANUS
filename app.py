"""
JANUS — Universal AI Cognitive Operating System.

This file only handles the shell: page config, sidebar "Core Orchestrator"
engine picker, and routing to the selected engine's render() function.
Each engine's actual logic lives in engines/<name>.py.
"""
import streamlit as st

from config import API_PROVIDER, MODEL_NAME
from engines import adie, codex, auin, uke

# Full roadmap per the JANUS product vision. ADIE, CODEX, AUIN, and UKE are
# real, working engines today — the rest are shown honestly as planned/
# in-development rather than faked, so the shell reflects the actual state
# of the build. Add a new engine by: (1) creating engines/<name>.py with a
# render() function, (2) adding an entry here with status="active", and
# (3) adding a branch in the routing block at the bottom of this file.
JANUS_ENGINES = [
    {"name": "ADIE", "full_name": "Advanced Deep Intelligence Engine", "icon": "🔍",
     "desc": "Investigates images, documents, and evidence with explainable reasoning.",
     "status": "active"},
    {"name": "CODEX", "full_name": "Software Engineering Intelligence", "icon": "💻",
     "desc": "Code generation, architecture, debugging, security review, ROCm guidance.",
     "status": "active"},
    {"name": "AUIN", "full_name": "Universal Intelligence Network", "icon": "🌐",
     "desc": "Live web + news search synthesized into cited, evidence-based answers.",
     "status": "active"},
    {"name": "UKE", "full_name": "Universal Knowledge Engine", "icon": "📚",
     "desc": "Cross-discipline academic and professional knowledge support.",
     "status": "active"},
    {"name": "UKPE", "full_name": "Universal Knowledge Processing Engine", "icon": "📄",
     "desc": "Summaries, notes, flashcards, and mind maps from large document sets.",
     "status": "roadmap"},
    {"name": "AMIE", "full_name": "Medical Intelligence Engine", "icon": "🩺",
     "desc": "Digital twin, 3D anatomy, disease and medicine intelligence.",
     "status": "roadmap"},
    {"name": "NAVIS", "full_name": "Navigation Intelligence", "icon": "🗺️",
     "desc": "Route planning and geographic reasoning via A*/Dijkstra.",
     "status": "roadmap"},
    {"name": "USE", "full_name": "Universal Simulation Engine", "icon": "🧪",
     "desc": "Interactive simulation across physics, chemistry, engineering, medicine.",
     "status": "roadmap"},
    {"name": "UDI", "full_name": "Universal Design Intelligence", "icon": "🏗️",
     "desc": "Idea → requirements → 3D model → simulation → engineering report.",
     "status": "roadmap"},
]

st.set_page_config(page_title="JANUS - Cognitive OS", page_icon="🧠", layout="wide")

# --- Sidebar: Core Orchestrator ---
with st.sidebar:
    st.markdown("## 🧠 JANUS")
    st.caption("Universal AI Cognitive Operating System")
    st.markdown("---")
    st.markdown("### Core Orchestrator")
    st.caption("Select an engine to route to.")

    engine_labels = [f"{e['icon']} {e['name']}" for e in JANUS_ENGINES]
    selected_label = st.radio(
        "Engine",
        engine_labels,
        label_visibility="collapsed",
        key="selected_engine_label",
    )
    selected_engine = JANUS_ENGINES[engine_labels.index(selected_label)]

    st.markdown(f"**{selected_engine['full_name']}**")
    st.caption(selected_engine["desc"])
    if selected_engine["status"] == "active":
        st.success("✅ Active", icon="✅")
    else:
        st.warning("🚧 On the roadmap — not built yet", icon="🚧")

    st.markdown("---")
    st.caption(f"Active backend: `{API_PROVIDER}` · `{MODEL_NAME}`")

st.title("🧠 JANUS — Universal AI Cognitive Operating System")

if selected_engine["name"] == "ADIE":
    adie.render()
elif selected_engine["name"] == "CODEX":
    codex.render()
elif selected_engine["name"] == "AUIN":
    auin.render()
elif selected_engine["name"] == "UKE":
    uke.render()
else:
    st.markdown(f"#### {selected_engine['icon']} {selected_engine['full_name']} _(Roadmap)_")
    st.info(
        f"**{selected_engine['name']}** is part of the JANUS product vision but isn't built yet.\n\n"
        f"Planned capability: {selected_engine['desc']}\n\n"
        "Switch to **🔍 ADIE**, **💻 CODEX**, **🌐 AUIN**, or **📚 UKE** in the sidebar to use the engines that are live today."
    )
