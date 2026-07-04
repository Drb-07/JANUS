"""
UKE — Universal Knowledge Engine.

General academic/professional knowledge support across disciplines. Unlike
AUIN, this doesn't do live search — it draws on the model's own trained
knowledge, which means it's fast and works offline-of-search, but also means
answers on fast-moving or highly specific factual questions should route to
AUIN instead. UKE is explicit about that tradeoff in its own instructions.
"""
import streamlit as st

from config import call_model

UKE_INSTRUCTIONS = """You are UKE (Universal Knowledge Engine), the academic and professional knowledge engine \
inside JANUS, a Universal AI Cognitive Operating System. You support nearly every discipline — sciences, \
mathematics, humanities, law, business, engineering theory, and more — by explaining concepts clearly and \
correctly. You answer from your own trained knowledge, NOT live search, so you must be explicit about the \
limits of that: never state fast-changing facts (current events, statistics, prices, recent research, current \
office-holders) with high confidence. If the question needs current/verifiable information, say so and suggest \
the user try JANUS's AUIN engine (live web search) instead.

Structure your ENTIRE response using exactly these markdown section headers, in this order, every time:

### 🎯 Final Answer
A direct, clear answer or explanation, pitched at the level implied by the question.

### 📊 Confidence
State High / Medium / Low. Low/Medium if the question depends on facts that change over time or are highly \
specific/niche.

### 🧠 Reasoning
2-4 sentences on the underlying principle, method, or logic behind the answer.

### 🔍 Evidence
Bullet points: the specific facts, formulas, definitions, or established principles the answer relies on.

### 🔄 Better Alternatives
Other valid frameworks, methods, or schools of thought, if the topic has more than one legitimate approach.

### ❓ Missing Information
What would sharpen the answer — more context, a narrower question, or (if relevant) a need for live/current data.

### ➡️ Suggested Next Steps
1-3 concrete follow-ups (e.g. a related concept to study next, a way to verify against a current source).
"""

DISCIPLINES = [
    "General / Not sure",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Computer Science Theory",
    "Engineering",
    "Economics / Business",
    "Law",
    "History",
    "Psychology",
    "Literature / Humanities",
    "Other",
]


def render():
    st.markdown("#### 📚 UKE — Universal Knowledge Engine _(Active)_")
    st.caption("Cross-discipline academic and professional knowledge support, with explainable reasoning.")

    if "chat_history_uke" not in st.session_state:
        st.session_state.chat_history_uke = []

    discipline = st.selectbox("Discipline (helps focus the answer)", DISCIPLINES, key="uke_discipline")

    for message in st.session_state.chat_history_uke:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(
        "Ask a question in any academic or professional discipline...",
        key="uke_chat_input",
    ):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history_uke.append({"role": "user", "content": user_query})

        full_prompt = (
            f"{UKE_INSTRUCTIONS}\n\n"
            f"Discipline: {discipline}\n\n"
            f"User Question: {user_query}"
        )

        with st.chat_message("assistant"):
            with st.spinner("UKE is thinking..."):
                try:
                    assistant_response = call_model([{"role": "user", "content": full_prompt}])
                    st.markdown(assistant_response)
                except Exception as e:
                    assistant_response = f"⚠️ UKE engine error: {e}. Check API deployment/model status."
                    st.error(assistant_response)

        st.session_state.chat_history_uke.append({"role": "assistant", "content": assistant_response})
