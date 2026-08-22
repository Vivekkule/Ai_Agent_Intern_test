from src.memory import ConversationMemory


def test_memory_stores_conversation():
    memory = ConversationMemory()

    memory.add_user_message("Where is my order?")
    memory.add_assistant_message("Please provide your order ID.")

    assert len(memory.messages) == 2
    assert memory.last_user_message() == "Where is my order?"
    assert memory.last_assistant_message() == "Please provide your order ID."


def test_memory_preserves_multi_turn_context():
    memory = ConversationMemory()

    memory.add_user_message("Tell me about my order ORD-1007.")
    memory.add_assistant_message("ORD-1007 is currently processing.")

    memory.add_user_message("What about its shipping?")

    messages = memory.get_messages()

    assert messages[0]["content"] == (
        "Tell me about my order ORD-1007."
    )

    assert messages[1]["content"] == (
        "ORD-1007 is currently processing."
    )

    assert messages[2]["content"] == (
        "What about its shipping?"
    )


def test_memory_has_bounded_size():
    memory = ConversationMemory(max_messages=4)

    for i in range(10):
        memory.add_user_message(f"message {i}")

    assert len(memory.messages) == 4
    assert memory.messages[0].content == "message 6"
    assert memory.messages[-1].content == "message 9"


def test_memory_can_clear():
    memory = ConversationMemory()

    memory.add_user_message("Hello")

    memory.clear()

    assert memory.messages == []