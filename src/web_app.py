from pathlib import Path
import sys

import streamlit as st

# Allow running:
# streamlit run src/web_app.py
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
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# Custom styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    /* Main application */
    .stApp {
        background: #f7f7f5;
    }

    /* Remove excessive top padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }

    /* Header */
    .brand {
        text-align: center;
        padding: 10px 0 5px 0;
    }

    .brand-title {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #171717;
        margin-bottom: 4px;
    }

    .brand-subtitle {
        color: #666666;
        font-size: 0.95rem;
    }

    /* Status badge */
    .status-container {
        text-align: center;
        margin: 12px 0 25px 0;
    }

    .status-badge {
        display: inline-block;
        padding: 6px 13px;
        border-radius: 20px;
        background: #e9f7ef;
        color: #176b3a;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Welcome box */
    .welcome {
        background: white;
        border: 1px solid #e6e6e6;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }

    .welcome-title {
        font-size: 1.35rem;
        font-weight: 650;
        color: #171717;
        margin-bottom: 8px;
    }

    .welcome-text {
        color: #666666;
        line-height: 1.6;
    }

    /* Source card */
    .source-card {
        background: #fafafa;
        border: 1px solid #e5e5e5;
        border-radius: 10px;
        padding: 12px 14px;
        margin-top: 8px;
        font-size: 0.85rem;
    }

    .source-label {
        font-weight: 650;
        color: #333333;
    }

    .source-text {
        color: #666666;
    }

    /* Handoff */
    .handoff {
        background: #fff8e6;
        border: 1px solid #f0d98c;
        color: #765900;
        padding: 12px 15px;
        border-radius: 10px;
        margin-top: 12px;
        font-size: 0.9rem;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #888888;
        font-size: 0.78rem;
        margin-top: 30px;
        padding-bottom: 10px;
    }

    /* Buttons */
    .stButton button {
        border-radius: 10px;
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

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    """
    <div class="brand">
        <div class="brand-title">
            Aster & Row
        </div>
        <div class="brand-subtitle">
            AI Customer Support Assistant
        </div>
    </div>

    <div class="status-container">
        <span class="status-badge">
            ● Local AI · Llama 3.1 · Ollama
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("### Aster & Row")

    st.markdown(
        """
        This assistant uses:

        - **BM25** knowledge retrieval
        - **Verified order tools**
        - **Conversation memory**
        - **Local Llama 3.1**
        - **Ollama**

        Your conversation is processed locally through
        the configured Ollama model.
        """
    )

    st.divider()

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
    ):
        st.session_state.agent.memory.clear()
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------

if not st.session_state.messages:

    st.markdown(
        """
        <div class="welcome">
            <div class="welcome-title">
                Hello! How can I help you today? 👋
            </div>

            <div class="welcome-text">
                Ask me about returns, shipping, warranties,
                international delivery, or your order.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Try asking")

    example_questions = [
        "How long does a regular customer have to return an unused backpack?",
        "Where is ORD-1007 and when should it arrive?",
        "Do you ship internationally?",
        "What about Canada, and how long does it take?",
    ]

    for question in example_questions:

        if st.button(
            question,
            key=f"example_{question}",
            use_container_width=True,
        ):
            st.session_state.pending_question = question
            st.rerun()


# ---------------------------------------------------------
# Display previous messages
# ---------------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):

            with st.expander(
                f"📚 Sources ({len(message['sources'])})"
            ):

                for index, source in enumerate(
                    message["sources"],
                    start=1,
                ):

                    st.markdown(
                        f"""
                        <div class="source-card">

                        <div class="source-label">
                        SOURCE {index}
                        </div>

                        <div class="source-text">
                        <b>File:</b> {source["filename"]}<br>
                        <b>Heading:</b> {source["heading"]}<br>
                        <b>Document:</b> {source["document_id"]}<br>
                        <b>Status:</b> {source["status"]}<br>
                        <b>Audience:</b> {source["audience"]}<br>
                        <b>Authority:</b>
                        {source["policy_authority"]}
                        </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        if message.get("handoff"):

            st.markdown(
                """
                <div class="handoff">
                    ⚠️ Human support review is recommended.
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------
# Get user input
# ---------------------------------------------------------

pending_question = st.session_state.pop(
    "pending_question",
    None,
)

user_input = st.chat_input(
    "Ask about returns, shipping, or your order..."
)

question = user_input or pending_question


# ---------------------------------------------------------
# Process question
# ---------------------------------------------------------

if question:

    # Display user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Generate response
    with st.chat_message("assistant"):

        with st.spinner("Checking our information..."):

            try:

                response = st.session_state.agent.answer(
                    question
                )

                answer = response.answer

                st.markdown(answer)

                # Store assistant message
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": response.sources,
                        "handoff": getattr(
                            response,
                            "handoff",
                            False,
                        ),
                    }
                )

                # Sources
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

                                <div class="source-label">
                                SOURCE {index}
                                </div>

                                <div class="source-text">
                                <b>File:</b>
                                {source["filename"]}<br>

                                <b>Heading:</b>
                                {source["heading"]}<br>

                                <b>Document:</b>
                                {source["document_id"]}<br>

                                <b>Status:</b>
                                {source["status"]}<br>

                                <b>Audience:</b>
                                {source["audience"]}<br>

                                <b>Authority:</b>
                                {source["policy_authority"]}
                                </div>

                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                # Human support warning
                if getattr(
                    response,
                    "handoff",
                    False,
                ):

                    st.markdown(
                        """
                        <div class="handoff">
                            ⚠️ Human support review is recommended.
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

                st.session_state.messages.append(
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
        Retrieval-Augmented Generation ·
        Local Ollama / Llama 3.1
    </div>
    """,
    unsafe_allow_html=True,
)