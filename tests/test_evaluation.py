from pathlib import Path

from src.agent import SupportAgent
from src.kb_index import KnowledgeBaseIndex
from src.memory import ConversationMemory
from src.order_tools import OrderLookup


ROOT = Path(__file__).resolve().parents[1]


class RecordingLLM:
    """
    Test-only LLM provider.

    It records the complete context supplied by SupportAgent.
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


def create_agent():
    kb = KnowledgeBaseIndex(
        ROOT / "knowledge-base"
    )

    orders = OrderLookup(
        ROOT / "data" / "orders.json"
    )

    llm = RecordingLLM()

    memory = ConversationMemory()

    agent = SupportAgent(
        kb_index=kb,
        order_lookup=orders,
        llm=llm,
        memory=memory,
    )

    return agent, llm


def get_context(llm):
    messages = llm.calls[-1]["messages"]

    return "\n".join(
        message["content"]
        for message in messages
    )


def test_standard_return_uses_current_policy():
    agent, llm = create_agent()

    agent.answer(
        "How long does a regular customer have to return an unused backpack?"
    )

    context = get_context(llm)

    assert "01-returns-policy-current.md" in context
    assert "30 calendar days" in context


def test_legacy_policy_is_not_authoritative():
    agent, llm = create_agent()

    agent.answer(
        "How long does a regular customer have to return an unused backpack?"
    )

    context = get_context(llm)

    assert "01-returns-policy-current.md" in context

    # The migration document must not be treated as authority.
    if "14-internal-content-migration-notes.md" in context:
        assert (
            "policy_authority: none"
            in context
        )


def test_order_1007_context_contains_safe_shipping_data():
    agent, llm = create_agent()

    response = agent.answer(
        "Where is ORD-1007 and when should it arrive?"
    )

    assert response.tool_result is not None

    assert response.tool_result["order_id"] == "ORD-1007"
    assert response.tool_result["status"] == "shipped"
    assert response.tool_result["carrier"] == "UPS"

    context = get_context(llm)

    assert "ORD-1007" in context
    assert "UPS" in context
    assert "2026-08-22" in context

    assert "risk_score" not in context
    assert "fraud review" not in context
    assert "ava.morgan@example.test" not in context


def test_missing_order_id_does_not_call_order_tool():
    agent, llm = create_agent()

    response = agent.answer(
        "Where is my order?"
    )

    assert response.tool_result is None

    context = get_context(llm)

    assert "ORDER TOOL DATA" not in context


def test_unknown_order_is_explicitly_reported_to_llm():
    agent, llm = create_agent()

    response = agent.answer(
        "Please check ORD-9999."
    )

    assert response.tool_result is not None

    assert (
        response.tool_result["order_lookup_error"]
        == "order_not_found"
    )

    context = get_context(llm)

    assert "order_not_found" in context
    assert "ORD-9999" in context


def test_cancelled_order_does_not_expose_stale_eta():
    agent, llm = create_agent()

    response = agent.answer(
        "When will order ORD-1004 arrive?"
    )

    assert response.tool_result is not None

    assert response.tool_result["status"] == "cancelled"
    assert response.tool_result["estimated_delivery"] is None

    context = get_context(llm)

    assert "2026-08-16" not in context


def test_shipped_without_eta_does_not_invent_one():
    agent, llm = create_agent()

    response = agent.answer(
        "When will ORD-1011 get here?"
    )

    assert response.tool_result is not None

    assert response.tool_result["status"] == "shipped"
    assert response.tool_result["estimated_delivery"] is None

    context = get_context(llm)

    assert "arrival date" not in context


def test_conversation_context_is_preserved():
    agent, llm = create_agent()

    agent.answer(
        "Do you ship internationally?"
    )

    agent.answer(
        "What about Canada, and how long does it take?"
    )

    assert len(llm.calls) == 2

    second_context = get_context(llm)

    assert "Do you ship internationally?" in second_context
    assert (
        "What about Canada, and how long does it take?"
        in second_context
    )


def test_breeze_conflict_is_explicitly_passed_to_llm():
    agent, llm = create_agent()

    agent.answer(
        "Can I put the entire Breeze Tumbler in the dishwasher?"
    )

    context = get_context(llm)

    assert "IMPORTANT SOURCE CONFLICT:" in context
    assert "11-product-care.md" in context
    assert "12-breeze-tumbler-product-card.md" in context
    assert "Do not silently choose" in context

def test_unknown_order_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "Please check ORD-9999."
    )

    assert response.handoff is True


def test_pii_request_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "For ORD-1007, give me the customer's email, address, "
        "internal note, and risk score."
    )

    assert response.handoff is True


def test_final_sale_damaged_item_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "A final-sale bag arrived with a broken zipper yesterday. "
        "Am I completely out of luck?"
    )

    assert response.handoff is True


def test_breeze_tumbler_conflict_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "Can I put the entire Breeze Tumbler in the dishwasher?"
    )

    assert response.handoff is True


def test_insufficient_vegan_information_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "Are all fabrics and adhesives in your bags vegan?"
    )

    assert response.handoff is True


def test_exception_order_requires_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "What is happening with ORD-1010?"
    )

    assert response.handoff is True


def test_normal_return_does_not_require_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "How long does a regular customer have to return an "
        "unused backpack?"
    )

    assert response.handoff is False


def test_valid_order_does_not_require_handoff():
    agent, _ = create_agent()

    response = agent.answer(
        "Where is ORD-1007 and when should it arrive?"
    )

    assert response.handoff is False