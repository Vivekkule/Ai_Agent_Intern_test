from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from .kb_index import KnowledgeBaseIndex
from .memory import ConversationMemory
from .order_tools import (
    InvalidOrderIdError,
    OrderLookup,
    OrderNotFoundError,
)
from .prompts import SYSTEM_PROMPT, build_context


class LLMProvider(Protocol):
    def generate(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        ...


@dataclass
class AgentResponse:
    answer: str
    sources: list[dict]
    tool_result: dict | None = None
    handoff: bool = False


class SupportAgent:
    ORDER_ID_PATTERN = re.compile(
        r"\bORD[\s\-/]*\d+\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        kb_index: KnowledgeBaseIndex,
        order_lookup: OrderLookup,
        llm: LLMProvider,
        memory: ConversationMemory | None = None,
    ):
        self.kb_index = kb_index
        self.order_lookup = order_lookup
        self.llm = llm
        self.memory = memory or ConversationMemory()

    def answer(self, user_message: str) -> AgentResponse:
        self.memory.add_user_message(user_message)

        # ---------------------------------------------------------
        # 1. Retrieve knowledge-base evidence
        # ---------------------------------------------------------
        retrieval = self.kb_index.search(
            user_message,
            top_k=5,
        )

        sources = []

        for result in retrieval.results:
            passage = result.passage

            sources.append(
                {
                    "filename": passage.filename,
                    "heading": passage.heading,
                    "document_id": passage.document_id,
                    "status": passage.metadata.status,
                    "audience": passage.metadata.audience,
                    "policy_authority": (
                        passage.metadata.policy_authority
                    ),
                    "text": passage.text,
                }
            )

        # ---------------------------------------------------------
        # 2. Detect an explicit order ID
        # ---------------------------------------------------------
        order_id = self._extract_order_id(user_message)

        tool_result = None

        if order_id is not None:
            tool_result = self._lookup_order(
                user_message=user_message,
                order_id=order_id,
            )

        # ---------------------------------------------------------
        # 3. Build trusted context
        # ---------------------------------------------------------
        context = build_context(
            sources,
            order_result=tool_result,
        )

        # Add conflict information explicitly.
        if retrieval.conflicts:
            conflict_lines = [
                "",
                "IMPORTANT SOURCE CONFLICT:",
                (
                    "Multiple active official customer-facing "
                    "sources may conflict."
                ),
            ]

            for group in retrieval.conflicts:
                for passage in group:
                    conflict_lines.append(
                        f"- {passage.filename} "
                        f"| {passage.heading}"
                    )

            conflict_lines.extend(
                [
                    "",
                    "Do not silently choose one conflicting "
                    "source.",
                    "Explain the conflict and provide safe "
                    "interim guidance or recommend human "
                    "confirmation.",
                ]
            )

            context += "\n".join(conflict_lines)

        # ---------------------------------------------------------
        # 4. Generate customer-facing answer
        # ---------------------------------------------------------
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "system",
                "content": context,
            },
            *self.memory.get_messages(),
        ]

        answer = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            messages=messages,
        )

        self.memory.add_assistant_message(answer)

        handoff = self._requires_handoff(
        user_message=user_message,
        tool_result=tool_result,
        has_conflict=bool(retrieval.conflicts),
        )

        return AgentResponse(
            answer=answer,
            sources=sources,
            tool_result=tool_result,
            handoff=handoff,
        )

    def _extract_order_id(
        self,
        user_message: str,
    ) -> str | None:
        match = self.ORDER_ID_PATTERN.search(user_message)

        if not match:
            return None

        return match.group(0)

    def _lookup_order(
        self,
        user_message: str,
        order_id: str,
    ) -> dict:
        """
        Select the smallest safe read-only order lookup required
        for the user's question.
        """
    
        query = user_message.lower()
    
        try:
            # Shipping / delivery questions need shipping data.
            if any(
                phrase in query
                for phrase in (
                    "where is",
                    "when will",
                    "when should",
                    "arrive",
                    "delivery",
                    "shipping",
                    "shipped",
                    "tracking",
                )
            ):
                return self.order_lookup.lookup_shipping(
                    order_id
                )

            # Membership questions need only membership data.
            if "membership" in query or "trailplus" in query:
                return self.order_lookup.lookup_membership(
                    order_id
                )

            # Product/item questions need sanitized item data.
            if any(
                phrase in query
                for phrase in (
                    "item",
                    "items",
                    "product",
                    "bag",
                    "backpack",
                    "tumbler",
                )
            ):
                return self.order_lookup.lookup_items(
                    order_id
                )

            # Cancellation questions need the cancellation window.
            if any(
                phrase in query
                for phrase in (
                    "cancel",
                    "cancellation",
                )
            ):
                return self.order_lookup.cancellation_window_status(
                    order_id
                )

            # General order question.
            return self.order_lookup.lookup(order_id)

        except InvalidOrderIdError:
            return {
                "order_lookup_error": "invalid_order_id",
                "order_id": order_id,
            }

        except OrderNotFoundError:
            return {
                "order_lookup_error": "order_not_found",
                "order_id": order_id,
            }

    def _requires_handoff(
        self,
        user_message: str,
        tool_result: dict | None,
        has_conflict: bool,
    ) -> bool:
        """
        Determine whether the case requires human support review.

        This is intentionally conservative and deterministic.
        The LLM does not control the handoff flag.
        """

        query = user_message.lower()

        # Genuine conflict between active authoritative sources.
        if has_conflict:
            return True

        # Unknown or invalid order requires support assistance.
        if tool_result is not None:
            error = tool_result.get("order_lookup_error")

            if error in {
                "order_not_found",
                "invalid_order_id",
            }:
                return True

            # Exception orders require support review.
            if tool_result.get("status") == "exception":
                return True

        # Never expose customer PII or internal information.
        sensitive_terms = (
            "email",
            "address",
            "phone number",
            "internal note",
            "risk score",
            "risk_score",
            "warehouse note",
            "support tags",
            "support_tags",
            "fraud review",
        )

        if any(term in query for term in sensitive_terms):
            return True

        # Final-sale damaged items require human review.
        if (
            "final-sale" in query
            or "final sale" in query
        ) and any(
            term in query
            for term in (
                "damaged",
                "broken",
                "zipper",
                "wrong item",
            )
        ):
            return True

        # The supplied knowledge base does not establish a
        # general vegan/material certification.
        if any(
            term in query
            for term in (
                "vegan",
                "vegan guarantee",
                "vegan certification",
            )
        ):
            return True

        return False    