from pathlib import Path

from src.kb_loader import KnowledgeBaseLoader


ROOT = Path(__file__).resolve().parents[1]


def test_load_knowledge_base():
    loader = KnowledgeBaseLoader(ROOT / "knowledge-base")

    passages = loader.load_documents()

    assert passages

    document_ids = {
        passage.document_id
        for passage in passages
    }

    assert "RET-2026-01" in document_ids
    assert "RET-2024-01" in document_ids
    assert "MIG-TEST-04" in document_ids


def test_current_returns_policy_metadata():
    loader = KnowledgeBaseLoader(ROOT / "knowledge-base")

    passages = loader.load_documents()

    current = [
        passage
        for passage in passages
        if passage.document_id == "RET-2026-01"
    ]

    assert current

    metadata = current[0].metadata

    assert metadata.status == "active"
    assert metadata.policy_authority == "official"
    assert metadata.audience == "customer"
    assert metadata.supersedes == "RET-2024-01"


def test_legacy_returns_policy_is_superseded():
    loader = KnowledgeBaseLoader(ROOT / "knowledge-base")

    passages = loader.load_documents()

    legacy = [
        passage
        for passage in passages
        if passage.document_id == "RET-2024-01"
    ]

    assert legacy

    assert legacy[0].metadata.status == "superseded"


def test_migration_notes_are_not_customer_authority():
    loader = KnowledgeBaseLoader(ROOT / "knowledge-base")

    passages = loader.load_documents()

    migration = [
        passage
        for passage in passages
        if passage.document_id == "MIG-TEST-04"
    ]

    assert migration

    metadata = migration[0].metadata

    assert metadata.status == "draft"
    assert metadata.audience == "internal"
    assert metadata.policy_authority == "none"
    assert metadata.customer_answering is False

from src.kb_index import KnowledgeBaseIndex


def test_current_returns_policy_has_higher_authority_than_legacy():
    index = KnowledgeBaseIndex(ROOT / "knowledge-base")

    current = next(
        passage
        for passage in index.passages
        if passage.document_id == "RET-2026-01"
    )

    legacy = next(
        passage
        for passage in index.passages
        if passage.document_id == "RET-2024-01"
    )

    assert index.authority_score(current) > index.authority_score(legacy)

    assert index.is_customer_authoritative(current)
    assert not index.is_customer_authoritative(legacy)


def test_migration_content_is_not_customer_authoritative():
    index = KnowledgeBaseIndex(ROOT / "knowledge-base")

    migration = next(
        passage
        for passage in index.passages
        if passage.document_id == "MIG-TEST-04"
    )

    assert not index.is_customer_authoritative(migration)
    assert index.authority_score(migration) < 0


def test_returns_query_prefers_current_policy():
    index = KnowledgeBaseIndex(ROOT / "knowledge-base")

    response = index.search(
        "How many days does a regular customer have to return an item?",
        top_k=5,
    )

    assert response.results

    authoritative_results = [
        result
        for result in response.results
        if result.passage.document_id == "RET-2026-01"
    ]

    assert authoritative_results


def test_migration_60_day_claim_is_not_authoritative():
    index = KnowledgeBaseIndex(ROOT / "knowledge-base")

    response = index.search(
        "Does everyone get 60 days to return every item?",
        top_k=10,
    )

    migration_results = [
        result
        for result in response.results
        if result.passage.document_id == "MIG-TEST-04"
    ]

    for result in migration_results:
        assert not index.is_customer_authoritative(result.passage)

from pathlib import Path

import pytest

from src.order_tools import (
    InvalidOrderIdError,
    OrderLookup,
    OrderNotFoundError,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def orders():
    return OrderLookup(
        ROOT / "data" / "orders.json"
    )


def test_order_id_normalization(orders):
    assert orders.normalize_order_id("ORD-1007") == "ORD-1007"
    assert orders.normalize_order_id("ord-1007") == "ORD-1007"
    assert orders.normalize_order_id(" ORD-1007 ") == "ORD-1007"
    assert orders.normalize_order_id("ORD/1007") == "ORD-1007"


def test_invalid_order_id_is_not_fuzzy_matched(orders):
    with pytest.raises(InvalidOrderIdError):
        orders.normalize_order_id("ORD-9999-XYZ")


def test_missing_order_is_not_guessed(orders):
    with pytest.raises(OrderNotFoundError):
        orders.lookup("ORD-9999")


def test_customer_pii_is_never_returned(orders):
    result = orders.lookup(
        "ORD-1007",
        fields={
            "order_id",
            "status",
            "membership_tier",
        },
    )

    assert "customer" not in result
    assert "name" not in result
    assert "email" not in result
    assert "shipping_address" not in result


def test_internal_fields_are_never_returned(orders):
    result = orders.lookup(
        "ORD-1005",
        fields={
            "order_id",
            "status",
            "customer_safe_message",
        },
    )

    assert "internal" not in result
    assert "risk_score" not in result
    assert "warehouse_note" not in result
    assert "support_tags" not in result


def test_items_are_sanitized(orders):
    result = orders.lookup_items("ORD-1005")

    assert result["order_id"] == "ORD-1005"

    item = result["items"][0]

    assert item["name"] == "Ridge Daypack"
    assert item["quantity"] == 1
    assert item["final_sale"] is False

    assert "sku" not in item


def test_cancelled_order_status_overrides_stale_shipping_data(orders):
    result = orders.lookup_shipping("ORD-1004")

    assert result["status"] == "cancelled"
    assert result["carrier"] is None
    assert result["tracking_number"] is None
    assert result["estimated_delivery"] is None


def test_shipped_without_eta_does_not_invent_eta(orders):
    result = orders.lookup_shipping("ORD-1011")

    assert result["status"] == "shipped"
    assert result["estimated_delivery"] is None


def test_exception_status_requires_support_review(orders):
    result = orders.lookup_status("ORD-1010")

    assert result["status"] == "exception"
    assert "support" in result["customer_safe_message"].lower()


def test_cancellation_window_uses_snapshot_time(orders):
    result = orders.cancellation_window_status("ORD-1001")

    assert result["snapshot_at"] == "2026-08-15T12:00:00Z"
    assert result["within_30_minute_window"] is True


def test_order_tool_is_read_only():
    """
    The OrderLookup API exposes lookup methods only.
    There should be no cancellation/refund/update operation.
    """

    public_methods = {
        name
        for name in dir(OrderLookup)
        if not name.startswith("_")
    }

    assert "cancel_order" not in public_methods
    assert "refund_order" not in public_methods
    assert "replace_order" not in public_methods
    assert "update_address" not in public_methods

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