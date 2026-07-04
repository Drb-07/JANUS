"""
AUIN — Universal Intelligence Network.

The full product vision (knowledge graphs across research papers, government
publications, maps, etc.) is far beyond a single build. What's genuinely
implemented here: live web + news search (via DuckDuckGo, no API key needed)
grounding a cited, evidence-based synthesis — the real substance behind
"combining information from search engines and news" from the vision doc.
"""
import streamlit as st

from config import call_model

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

AUIN_INSTRUCTIONS = """You are AUIN (Universal Intelligence Network), the knowledge synthesis engine inside \
JANUS, a Universal AI Cognitive Operating System. You build evidence-based answers by combining live web/news \
search results. Ground your answer in the numbered search results provided — never invent sources, URLs, or \
facts not present in them. If the results are thin or contradictory, say so rather than filling gaps with \
unstated assumptions.

Structure your ENTIRE response using exactly these markdown section headers, in this order, every time:

### 🎯 Final Answer
A direct, concise answer. Cite sources inline as [1], [2], etc., matching the numbered results provided.

### 📊 Confidence
State High / Medium / Low, with a one-sentence justification (e.g. multiple corroborating sources vs. one weak source).

### 🧠 Reasoning
2-4 sentences on how the search results were synthesized into this answer.

### 🔍 Evidence
Bullet points, each citing a specific numbered source and what it contributes.

### 🔗 Sources
A numbered list matching the citations used, with source title and URL.

### 🔄 Better Alternatives
Other interpretations, or conflicting information found across sources. If none, say so.

### ❓ Missing Information
What additional search, source type, or date range would improve confidence.

### ➡️ Suggested Next Steps
1-3 concrete follow-up actions (e.g. narrower search, checking a primary source directly).

If no search results are provided below (search failed or returned nothing), say so explicitly under Confidence \
and answer cautiously from general knowledge, clearly flagged as ungrounded/not search-verified.
"""


def run_web_search(query, max_results=5):
    """Run a text + news search via DuckDuckGo. Returns a list of dicts with
    title/url/body, or an empty list if search is unavailable/fails."""
    if not DDGS_AVAILABLE:
        return []
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", "Untitled"),
                    "url": r.get("href", ""),
                    "body": r.get("body", ""),
                    "kind": "web",
                })
            for r in ddgs.news(query, max_results=max(2, max_results // 2)):
                results.append({
                    "title": r.get("title", "Untitled"),
                    "url": r.get("url", ""),
                    "body": r.get("body", ""),
                    "kind": "news",
                })
    except Exception:
        # Search backend can be rate-limited/blocked on some cloud IPs — fail
        # soft rather than crashing the engine; the prompt tells the model to
        # flag ungrounded answers when results list is empty.
        return results
    return results


def format_search_context(results):
    if not results:
        return "(No search results available.)"
    lines = []
    for i, r in enumerate(results, start=1):
        tag = "📰" if r["kind"] == "news" else "🌐"
        lines.append(f"[{i}] {tag} {r['title']}\nURL: {r['url']}\nSnippet: {r['body']}\n")
    return "\n".join(lines)


def render():
    st.markdown("#### 🌐 AUIN — Universal Intelligence Network _(Active)_")
    st.caption("Live web + news search, synthesized into a cited, evidence-based answer.")

    if not DDGS_AVAILABLE:
        st.error(
            "The `ddgs` package isn't installed, so AUIN can't run live search. "
            "Add `ddgs` to requirements.txt and redeploy."
        )
        return

    if "chat_history_auin" not in st.session_state:
        st.session_state.chat_history_auin = []

    max_results = st.slider("Search depth (results to pull in)", min_value=3, max_value=10, value=5, key="auin_depth")

    for message in st.session_state.chat_history_auin:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(
        "Ask something that benefits from current information...",
        key="auin_chat_input",
    ):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history_auin.append({"role": "user", "content": user_query})

        with st.chat_message("assistant"):
            with st.spinner("Searching and synthesizing..."):
                search_results = run_web_search(user_query, max_results=max_results)
                search_context = format_search_context(search_results)

                full_prompt = (
                    f"{AUIN_INSTRUCTIONS}\n\n"
                    f"Search Results:\n{search_context}\n\n"
                    f"User Question: {user_query}"
                )

                try:
                    assistant_response = call_model([{"role": "user", "content": full_prompt}])
                    st.markdown(assistant_response)
                except Exception as e:
                    assistant_response = f"⚠️ AUIN engine error: {e}. Check API deployment/model status."
                    st.error(assistant_response)

            if search_results:
                with st.expander(f"🔍 Raw search results used ({len(search_results)})"):
                    for i, r in enumerate(search_results, start=1):
                        tag = "📰" if r["kind"] == "news" else "🌐"
                        st.markdown(f"**[{i}] {tag} [{r['title']}]({r['url']})**")
                        st.caption(r["body"])
            else:
                st.caption("⚠️ No live search results returned — answer above may be ungrounded. See its Confidence section.")

        st.session_state.chat_history_auin.append({"role": "assistant", "content": assistant_response})
