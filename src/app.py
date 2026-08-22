from pathlib import Path

from .agent import SupportAgent
from .kb_index import KnowledgeBaseIndex
from .memory import ConversationMemory
from .ollama_provider import OllamaProvider
from .order_tools import OrderLookup


ROOT = Path(__file__).resolve().parents[1]


def create_agent() -> SupportAgent:
    """
    Build the complete support agent.
    """

    kb_index = KnowledgeBaseIndex(
        ROOT / "knowledge-base"
    )

    order_lookup = OrderLookup(
        ROOT / "data" / "orders.json"
    )

    llm = OllamaProvider(
        model="llama3.1:latest"
    )

    memory = ConversationMemory()

    return SupportAgent(
        kb_index=kb_index,
        order_lookup=order_lookup,
        llm=llm,
        memory=memory,
    )


def main() -> None:
    print("=" * 60)
    print("Aster & Row — RAG Support Agent")
    print("Powered by local Ollama / Llama 3.1")
    print("=" * 60)
    print()
    print("Type 'exit' or 'quit' to end the conversation.")
    print()

    agent = create_agent()

    while True:
        try:
            user_message = input("You: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_message:
            continue

        if user_message.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            response = agent.answer(user_message)

            print()
            print(f"Agent: {response.answer}")

            if response.handoff:
                print()
                print(
                    "⚠ Human support review is recommended."
                )

            print()

        except Exception as exc:
            print()
            print(
                "Agent: I’m sorry, but I couldn't process "
                "that request safely."
            )
            print(
                "Please contact customer support for assistance."
            )
            print()

            # Keep technical details out of the customer response.
            print(
                f"[Internal error: {type(exc).__name__}]"
            )


if __name__ == "__main__":
    main()