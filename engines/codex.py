"""
CODEX — Software Engineering Intelligence.

Code generation, architecture design, debugging, performance optimization,
security review, and AMD ROCm guidance, using the Explainable AI response
format shared with every other JANUS engine.
"""
import streamlit as st

from config import call_model

CODEX_INSTRUCTIONS = """You are CODEX, the Software Engineering Intelligence engine inside JANUS, a Universal \
AI Cognitive Operating System. You help with code generation, architecture design, debugging, performance \
optimization, security review, and AMD ROCm/GPU-compute guidance. Never fabricate APIs, flags, or behavior you \
aren't confident about — flag uncertainty explicitly instead.

Structure your ENTIRE response using exactly these markdown section headers, in this order, every time:

### 🎯 Final Answer
The solution, code, or direct answer. Use fenced code blocks with the correct language tag for any code.

### 📊 Confidence
State High / Medium / Low, with a one-sentence justification (e.g. untested, version-dependent, assumes X).

### 🧠 Reasoning
2-4 sentences on the approach/design decisions behind the answer.

### 🔍 Evidence
Bullet points: relevant language/framework/hardware facts, complexity analysis, or known behavior that supports the answer.

### 🔄 Better Alternatives
Other valid approaches and their tradeoffs. If none, say so.

### ❓ Missing Information
What context (target hardware, ROCm version, constraints, existing codebase) would sharpen the answer.

### ➡️ Suggested Next Steps
1-3 concrete follow-up actions (e.g. tests to add, benchmarks to run, profiling to do).
"""


def render():
    st.markdown("#### 💻 CODEX — Software Engineering Intelligence _(Active)_")
    st.caption("Code generation, architecture, debugging, optimization, security review, and AMD ROCm guidance.")

    if "chat_history_codex" not in st.session_state:
        st.session_state.chat_history_codex = []

    task_focus = st.selectbox(
        "Task focus",
        [
            "General / Not sure",
            "Generate Code",
            "Architecture Design",
            "Debug an Error",
            "Performance Optimization",
            "Security Review",
            "AMD ROCm Guidance",
        ],
        key="codex_task_focus",
    )

    for message in st.session_state.chat_history_codex:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(
        "Describe your task, paste code, or paste an error message...",
        key="codex_chat_input",
    ):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history_codex.append({"role": "user", "content": user_query})

        full_prompt = (
            f"{CODEX_INSTRUCTIONS}\n\n"
            f"Task Focus: {task_focus}\n\n"
            f"User Request:\n{user_query}"
        )

        with st.chat_message("assistant"):
            with st.spinner("CODEX is working..."):
                try:
                    assistant_response = call_model([{"role": "user", "content": full_prompt}])
                    st.markdown(assistant_response)
                except Exception as e:
                    assistant_response = f"⚠️ CODEX engine error: {e}. Check API deployment/model status."
                    st.error(assistant_response)

        st.session_state.chat_history_codex.append({"role": "assistant", "content": assistant_response})
