from pathlib import Path

from src.agent import SupportAgent
from src.kb_index import KnowledgeBaseIndex
from src.memory import ConversationMemory
from src.order_tools import OrderLookup


ROOT = Path(__file__).resolve().parents[1]


class FakeLLM:
    """
    Deterministic LLM provider used only for testing.

    It records what the agent sends to the model and returns
    a predictable response.
    """

    def __init__(self):
        self.calls = []

    def generate(self, system_prompt, messages):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "messages": messages,
            }
        )

        return "TEST RESPONSE"


def build_agent():
    kb = KnowledgeBaseIndex(
        ROOT / "knowledge-base"
    )

    orders = OrderLookup(
        ROOT / "data" / "orders.json"
    )

    llm = FakeLLM()

    memory = ConversationMemory()

    agent = SupportAgent(
        kb_index=kb,
        order_lookup=orders,
        llm=llm,
        memory=memory,
    )

    return agent, llm


def test_agent_returns_llm_answer():
    agent, llm = build_agent()

    response = agent.answer(
        "How long does a regular customer have to return an unused backpack?"
    )

    assert response.answer == "TEST RESPONSE"
    assert len(llm.calls) == 1


def test_agent_retrieves_current_return_policy():
    agent, _ = build_agent()

    response = agent.answer(
        "How long does a regular customer have to return an unused backpack?"
    )

    filenames = {
        source["filename"]
        for source in response.sources
    }

    assert "01-returns-policy-current.md" in filenames


def test_agent_uses_shipping_tool_for_order_question():
    agent, _ = build_agent()

    response = agent.answer(
        "Where is ORD-1007 and when should it arrive?"
    )

    assert response.tool_result is not None

    assert response.tool_result["order_id"] == "ORD-1007"
    assert response.tool_result["status"] == "shipped"
    assert response.tool_result["carrier"] == "UPS"
    assert (
        response.tool_result["estimated_delivery"]
        == "2026-08-22"
    )


def test_agent_does_not_call_order_tool_without_order_id():
    agent, _ = build_agent()

    response = agent.answer(
        "Where is my order?"
    )

    assert response.tool_result is None


def test_agent_unknown_order_is_not_guessed():
    agent, _ = build_agent()

    response = agent.answer(
        "Please check ORD-9999."
    )

    assert response.tool_result is not None

    assert (
        response.tool_result["order_lookup_error"]
        == "order_not_found"
    )

    assert response.tool_result["order_id"] == "ORD-9999"


def test_agent_order_result_contains_no_customer_pii():
    agent, _ = build_agent()

    response = agent.answer(
        "Where is ORD-1007?"
    )

    tool_result = response.tool_result

    assert tool_result is not None

    forbidden = {
        "email",
        "name",
        "shipping_address",
        "address",
        "risk_score",
        "warehouse_note",
        "support_tags",
    }

    assert forbidden.isdisjoint(tool_result.keys())


def test_agent_preserves_conversation_memory():
    agent, llm = build_agent()

    agent.answer(
        "Do you ship internationally?"
    )

    agent.answer(
        "What about Canada?"
    )

    assert len(llm.calls) == 2

    second_messages = llm.calls[1]["messages"]

    user_messages = [
        message["content"]
        for message in second_messages
        if message["role"] == "user"
    ]

    assert "Do you ship internationally?" in user_messages
    assert "What about Canada?" in user_messages


def test_agent_returns_sources():
    agent, _ = build_agent()

    response = agent.answer(
        "Do all products have a lifetime warranty?"
    )

    assert response.sources

    filenames = {
        source["filename"]
        for source in response.sources
    }

    assert "07-warranty.md" in filenames