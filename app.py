"""
JANUS — Universal AI Cognitive Operating System.

This file only handles the shell: page config, sidebar "Core Orchestrator"
engine picker, and routing to the selected engine's render() function.

IMPORTANT: this file auto-discovers engines from the engines/ folder. To add
a new working engine, you do NOT need to edit this file:

    1. Create engines/<name>.py
    2. Give it an ENGINE dict: {"name", "full_name", "icon", "desc", "order"}
    3. Give it a render() function that draws its UI
    4. (Optional) remove its placeholder entry from roadmap.py, if it had one

That's it — this file will pick it up automatically on next run.
"""
import importlib
import pkgutil

import streamlit as st

import engines
from config import API_PROVIDER, MODEL_NAME
from roadmap import ROADMAP_ENGINES


def discover_engines():
    """Import every module in engines/ that exposes an ENGINE dict + render().
    Modules starting with "_" are skipped (for shared helpers, not engines).
    Returns (list_of_engine_metadata, {name: render_function})."""
    discovered = []
    render_fns = {}
    for module_info in pkgutil.iter_modules(engines.__path__):
        module_name = module_info.name
        if module_name.startswith("_"):
            continue
        module = importlib.import_module(f"engines.{module_name}")
        if not hasattr(module, "ENGINE") or not hasattr(module, "render"):
            # Not a valid engine module (missing metadata or render()) — skip
            # silently rather than crashing the whole app over one bad file.
            continue
        meta = dict(module.ENGINE)
        meta["status"] = "active"
        discovered.append(meta)
        render_fns[meta["name"]] = module.render
    return discovered, render_fns


active_engines, render_fns = discover_engines()
active_names = {e["name"] for e in active_engines}

# Roadmap entries only show if no real module has claimed that name yet —
# so the moment you build a real engines/navis.py, NAVIS automatically
# disappears from "roadmap" and appears as "active" with zero edits here.
roadmap_engines = [dict(e, status="roadmap") for e in ROADMAP_ENGINES if e["name"] not in active_names]

JANUS_ENGINES = sorted(active_engines + roadmap_engines, key=lambda e: e.get("order", 999))

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

if selected_engine["status"] == "active":
    render_fns[selected_engine["name"]]()
else:
    active_list = ", ".join(f"**{e['icon']} {e['name']}**" for e in active_engines)
    st.markdown(f"#### {selected_engine['icon']} {selected_engine['full_name']} _(Roadmap)_")
    st.info(
        f"**{selected_engine['name']}** is part of the JANUS product vision but isn't built yet.\n\n"
        f"Planned capability: {selected_engine['desc']}\n\n"
        f"Switch to one of the active engines in the sidebar to use what's live today: {active_list}."
    )
