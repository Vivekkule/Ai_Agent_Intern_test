from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------
# Project root / imports
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app import create_agent


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Aster & Row | AI Support",
    page_icon="👜",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    /* Overall page */
    .stApp {
        background-color: #f6f4ef;
    }

    .block-container {
        max-width: 920px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* Header */
    .header {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
    }

    .brand {
        font-size: 2.2rem;
        font-weight: 750;
        color: #1c1c1c;
        letter-spacing: -0.8px;
    }

    .tagline {
        margin-top: 0.35rem;
        color: #6f6f6f;
        font-size: 0.98rem;
    }

    .status {
        display: inline-block;
        margin-top: 0.8rem;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        background: #eaf6ee;
        color: #23653c;
        font-size: 0.78rem;
        font-weight: 650;
    }

    /* Welcome */
    .welcome {
        background: #ffffff;
        border: 1px solid #e7e4dc;
        border-radius: 18px;
        padding: 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
    }

    .welcome-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #202020;
    }

    .welcome-text {
        margin-top: 0.45rem;
        color: #6b6b6b;
        line-height: 1.6;
    }

    /* Source cards */
    .source-card {
        border: 1px solid #e5e1d8;
        border-radius: 12px;
        background: #fbfaf7;
        padding: 0.85rem;
        margin-top: 0.6rem;
    }

    .source-title {
        font-size: 0.8rem;
        font-weight: 700;
        color: #3a3a3a;
        margin-bottom: 0.35rem;
    }

    .source-meta {
        font-size: 0.78rem;
        color: #6e6e6e;
        line-height: 1.5;
    }

    /* Handoff */
    .handoff {
        margin-top: 0.8rem;
        padding: 0.8rem 0.95rem;
        border-radius: 11px;
        background: #fff7df;
        border: 1px solid #efd58b;
        color: #725a16;
        font-size: 0.87rem;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #8b8b8b;
        font-size: 0.75rem;
        margin-top: 2rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f1eee7;
    }
    /* Chat message text */
.stChatMessage,
.stChatMessage p,
.stChatMessage li,
.stChatMessage span,
.stMarkdown,
.stMarkdown p,
.stMarkdown li {
    color: #111111 !important;
}

/* User and assistant message text */
[data-testid="stChatMessageContent"] {
    color: #111111 !important;
}

/* Expanders and source text */
[data-testid="stExpander"] p,
[data-testid="stExpander"] span {
    color: #222222 !important;
}

/* Sidebar text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] span {
    color: #222222 !important;
}

/* Chat/output text only */
[data-testid="stChatMessageContent"] {
    color: #111111 !important;
}

[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li,
[data-testid="stChatMessageContent"] span {
    color: #111111 !important;
}

/* Source/expander text */
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] span {
    color: #222222 !important;
}

/* Sidebar text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] span {
    color: #222222 !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    """
    <div class="header">
        <div class="brand">Aster & Row</div>
        <div class="tagline">
            Customer Support Assistant
        </div>
        <div class="status">
            ● Local AI · Llama 3.1 · Ollama
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("### Aster & Row")

    st.write(
        "Reliable customer support powered by "
        "retrieval, verified order data, conversation "
        "memory, and a local LLM."
    )

    st.divider()

    st.markdown("#### System")

    st.write("✅ BM25 knowledge retrieval")
    st.write("✅ Read-only order tools")
    st.write("✅ Conversation memory")
    st.write("✅ Customer-data protection")
    st.write("✅ Ollama / Llama 3.1")

    st.divider()

    if st.button(
        "🗑️ New conversation",
        use_container_width=True,
    ):
        st.session_state.agent.memory.clear()
        st.session_state.chat_history = []
        st.rerun()


# ---------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------

if not st.session_state.chat_history:

    st.markdown(
        """
        <div class="welcome">
            <div class="welcome-title">
                Hello! How can I help you today? 👋
            </div>

            <div class="welcome-text">
                Ask me about returns, shipping, warranties,
                international delivery, or an order.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Try a question")

    examples = [
        "How long does a regular customer have to return an unused backpack?",
        "Where is ORD-1007 and when should it arrive?",
        "Do you ship internationally?",
        "What about Canada, and how long does it take?",
    ]

    for index, question in enumerate(examples):

        if st.button(
            question,
            key=f"example_{index}",
            use_container_width=True,
        ):
            st.session_state.pending_question = question
            st.rerun()


# ---------------------------------------------------------
# Render previous chat
# ---------------------------------------------------------

for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        sources = message.get("sources", [])

        if message["role"] == "assistant" and sources:

            with st.expander(
                f"📚 Sources ({len(sources)})"
            ):

                for index, source in enumerate(
                    sources,
                    start=1,
                ):

                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div class="source-title">
                                SOURCE {index}
                            </div>

                            <div class="source-meta">
                                <b>File:</b>
                                {source["filename"]}<br>

                                <b>Heading:</b>
                                {source["heading"]}<br>

                                <b>Document:</b>
                                {source["document_id"]}<br>

                                <b>Status:</b>
                                {source["status"]}<br>

                                <b>Authority:</b>
                                {source["policy_authority"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        if (
            message["role"] == "assistant"
            and message.get("handoff", False)
        ):

            st.markdown(
                """
                <div class="handoff">
                    ⚠️ Human support review is recommended
                    for this request.
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------
# Input
# ---------------------------------------------------------

pending = st.session_state.pending_question
st.session_state.pending_question = None

typed_question = st.chat_input(
    "Ask about returns, shipping, warranties, or your order..."
)

question = typed_question or pending


# ---------------------------------------------------------
# Process question
# ---------------------------------------------------------

if question:

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Checking verified information..."):

            try:
                response = st.session_state.agent.answer(
                    question
                )

                st.markdown(response.answer)

                assistant_message = {
                    "role": "assistant",
                    "content": response.answer,
                    "sources": response.sources,
                    "handoff": getattr(
                        response,
                        "handoff",
                        False,
                    ),
                }

                st.session_state.chat_history.append(
                    assistant_message
                )

                if response.sources:

                    with st.expander(
                        f"📚 Sources ({len(response.sources)})"
                    ):

                        for index, source in enumerate(
                            response.sources,
                            start=1,
                        ):

                            st.markdown(
                                f"""
                                <div class="source-card">
                                    <div class="source-title">
                                        SOURCE {index}
                                    </div>

                                    <div class="source-meta">
                                        <b>File:</b>
                                        {source["filename"]}<br>

                                        <b>Heading:</b>
                                        {source["heading"]}<br>

                                        <b>Document:</b>
                                        {source["document_id"]}<br>

                                        <b>Status:</b>
                                        {source["status"]}<br>

                                        <b>Authority:</b>
                                        {source["policy_authority"]}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                if getattr(
                    response,
                    "handoff",
                    False,
                ):

                    st.markdown(
                        """
                        <div class="handoff">
                            ⚠️ Human support review is recommended
                            for this request.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            except Exception:
                error_message = (
                    "I'm sorry, but I couldn't process "
                    "that request safely. Please contact "
                    "customer support for assistance."
                )

                st.error(error_message)

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "sources": [],
                        "handoff": True,
                    }
                )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        Aster & Row AI Support ·
        RAG · Local Ollama · Llama 3.1
    </div>
    """,
    unsafe_allow_html=True,
)