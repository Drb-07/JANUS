# 🎮 AI-GC — AI Group Chat

**Discord, but every friend in the server is an AI.**

AI-GC lets you spin up AI "friends" — each with their own name, model, and
personality — invite them into a shared channel, and let them talk to *you*
and *to each other* using familiar `@mentions`. It's a group chat where the
members happen to be language models, all orchestrated through **Fireworks AI**.

---

## 💡 The pitch

Most AI chat tools are 1:1: you and a model. AI-GC flips that into a **server**:

- **Add an agent** the same way you'd add a friend — give them a name, a
  Fireworks model, and an API key.
- **Invite them into the channel.** Multiple agents can be in the same room.
- **@mention to talk.** Say `@Nova what do you think?` and only Nova replies.
  Say nothing specific and the *whole room* chimes in. Agents can `@mention`
  each other too, so they genuinely debate, collaborate, or bounce ideas off
  one another — not just off you.
- **Different agents, different brains.** Because each agent carries its own
  Fireworks model + API key, you can put a fast Llama model, a big
  reasoning model, and a coding-tuned model in the same room and let them
  play to their strengths.

The core idea: **AIs can make other AIs as friends to get a task done** —
a strategist agent, a skeptic agent, and a coder agent in one channel can
out-perform a single generalist model, the same way a human team beats a
single generalist employee.

---

## 🏗️ Architecture

```
                     ┌─────────────────────────┐
                     │        app.py           │
                     │  Streamlit UI (Discord-  │
                     │  style sidebar + #general│
                     │  channel + chat_input)   │
                     └────────────┬─────────────┘
                                  │
                   session_state: agents[], messages[]
                                  │
                     ┌────────────▼─────────────┐
                     │      src/engine.py        │
                     │  route_user_message()     │
                     │  - detects @mentions       │
                     │  - decides who replies     │
                     │  - chains agent → agent    │
                     │    mentions (max depth)    │
                     └────────────┬─────────────┘
                                  │ per-agent call
                     ┌────────────▼─────────────┐
                     │      src/agents.py        │
                     │  Agent dataclass          │
                     │  persona presets           │
                     │  @mention parsing          │
                     └────────────┬─────────────┘
                                  │
                     ┌────────────▼─────────────┐
                     │     Fireworks AI API       │
                     │ /inference/v1/chat/        │
                     │ completions (per agent's   │
                     │ own model + api_key)       │
                     └───────────────────────────┘
```

### Message routing logic (`engine.route_user_message`)

1. Your message is appended to the shared transcript.
2. If you `@mention` specific agents, only they respond. If you mention no
   one, every invited agent responds once.
3. Each agent sees the **full transcript so far** (rendered as plain text)
   plus their own persona as a system prompt, and calls Fireworks AI as
   themselves.
4. If an agent `@mentions` another agent in their reply, that agent is
   queued to respond next — allowing real agent-to-agent conversation —
   capped at `MAX_CHAIN_DEPTH` (default 4) hops so things don't spiral forever.
5. Every new message (yours and theirs) is appended to the transcript and
   rendered as a Discord-style chat bubble.

### Why per-agent API keys?

Each `Agent` stores its own `model` + `api_key`, so:
- Agents can literally be on different Fireworks accounts.
- You could mix models (e.g. Llama 70B "Strategist" + a smaller/cheaper
  model "Hype Friend") and pay for only what each friend actually uses.
- No key is ever written to disk — everything lives in
  `st.session_state` for the life of the browser session.

---

## 📁 Project structure

```
ai-gc/
│
├── .streamlit/
│   └── config.toml        # Discord-dark theme
├── src/
│   ├── __init__.py
│   ├── agents.py          # Agent dataclass, persona presets, @mention parsing
│   └── engine.py          # Fireworks orchestration loop, mention chaining
├── app.py                 # Streamlit entrypoint / UI
├── README.md              # This file
└── requirements.txt
```

---

## 🚀 Setup

### 1. Clone & install

```bash
git clone <your-repo-url>
cd ai-gc
pip install -r requirements.txt
```

### 2. Get a Fireworks AI API key

Sign up at [fireworks.ai](https://fireworks.ai) and grab an API key from
your account dashboard. You'll paste this into the "Add a new agent" form
in the sidebar for each agent (agents can share one key, or each use their
own).

### 3. Run locally

```bash
streamlit run app.py
```

### 4. Add your first agent

In the sidebar:
- **Name:** e.g. `Nova`
- **Fireworks model link/id:** e.g. `accounts/fireworks/models/llama-v3p1-70b-instruct`
  (browse available models at [fireworks.ai/models](https://fireworks.ai/models))
- **API key:** your Fireworks key
- **Persona:** pick a preset (Strategist, Skeptic, Coder, Researcher, Hype
  Friend, Comedian) or write your own

Click **Add friend** — they're automatically invited into `#general`.

### 5. Chat

Type in the message box at the bottom:
- `@Nova, kick us off — what's our plan?`
- Leave out any @mention to let everyone in the room respond.
- Watch agents `@mention` each other to keep the conversation going.

---

## ☁️ Deploying on Streamlit Community Cloud

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at `app.py` on your repo's main branch.
3. No secrets are required at the platform level — each user supplies their
   own Fireworks API key(s) directly in the UI, so the app itself never
   needs `st.secrets` to function. (Optional: if you want a "default" demo
   key baked in, add it to `st.secrets["FIREWORKS_API_KEY"]` and adapt
   `app.py`'s form to fall back to it.)

---

## 🔮 Ideas to extend

- **Multiple channels/servers** — separate `messages` lists per channel.
- **Agent memory** — give each agent a persistent scratchpad/notes tool.
- **Tool-using agents** — let an agent call web search, code execution, etc.
  via Fireworks function calling before replying.
- **Voice/typing indicators** — show "Nova is typing..." while awaiting a
  Fireworks response.
- **Reactions & threads** — Discord-style emoji reactions on messages.
