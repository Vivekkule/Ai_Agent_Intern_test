from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OrderNotFoundError(Exception):
    """Raised when an order ID does not exist."""


class InvalidOrderIdError(Exception):
    """Raised when the supplied value is not a usable order ID."""


class OrderLookup:
    """
    Safe read-only interface over the mock orders dataset.

    Important:
    - Only customer-safe fields are returned.
    - Internal/customer PII is never returned.
    - The tool does not perform mutations.
    """

    SAFE_TOP_LEVEL_FIELDS = {
        "order_id",
        "membership_tier",
        "placed_at",
        "status",
        "status_updated_at",
        "shipped_at",
        "delivered_at",
        "carrier",
        "tracking_number",
        "estimated_delivery",
        "customer_safe_message",
    }

    SAFE_ITEM_FIELDS = {
        "name",
        "quantity",
        "final_sale",
    }

    def __init__(self, orders_path: str | Path):
        self.orders_path = Path(orders_path)

        data = json.loads(
            self.orders_path.read_text(encoding="utf-8")
        )

        self.snapshot_at = data["snapshot_at"]

        self._orders = {
            order["order_id"]: order
            for order in data["orders"]
        }

    def normalize_order_id(self, value: str) -> str:
        """
        Normalize harmless formatting differences.

        Examples:
            "ord-1007"       -> "ORD-1007"
            " ORD-1007 "     -> "ORD-1007"
            "ORD 1007"       -> "ORD-1007"
            "ORD/1007"       -> "ORD-1007"

        We do NOT attempt fuzzy matching.
        """

        if not isinstance(value, str):
            raise InvalidOrderIdError(
                "Order ID must be a string."
            )

        normalized = value.strip().upper()

        # Remove ordinary punctuation/whitespace.
        normalized = re.sub(r"[^A-Z0-9]", "", normalized)

        # Reconstruct the expected ORD-#### form.
        match = re.fullmatch(r"ORD(\d+)", normalized)

        if not match:
            raise InvalidOrderIdError(
                f"Invalid order ID format: {value!r}"
            )

        return f"ORD-{match.group(1)}"

    def lookup(
        self,
        order_id: str,
        fields: set[str] | None = None,
    ) -> dict[str, Any]:
        """
        Look up an order and return only requested safe fields.

        If fields is None, return a conservative default set.
        """

        normalized_id = self.normalize_order_id(order_id)

        order = self._orders.get(normalized_id)

        if order is None:
            raise OrderNotFoundError(
                f"No order found for {normalized_id}"
            )

        if fields is None:
            fields = {
                "order_id",
                "status",
                "membership_tier",
                "items",
                "customer_safe_message",
            }

        result: dict[str, Any] = {}

        for field in fields:
            if field == "items":
                result["items"] = self._safe_items(
                    order.get("items", [])
                )
                continue

            if field not in self.SAFE_TOP_LEVEL_FIELDS:
                continue

            if field in order:
                result[field] = order[field]

        return result

    def lookup_status(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Return the minimum fields required for a status question.
        """

        order = self.lookup(
            order_id,
            fields={
                "order_id",
                "status",
                "status_updated_at",
                "customer_safe_message",
            },
        )

        # Explicitly apply status precedence.
        return self._apply_status_precedence(order)

    def lookup_shipping(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Return shipping information.

        Status remains authoritative.
        """

        order = self.lookup(
            order_id,
            fields={
                "order_id",
                "status",
                "shipped_at",
                "delivered_at",
                "carrier",
                "tracking_number",
                "estimated_delivery",
                "customer_safe_message",
            },
        )

        return self._apply_status_precedence(order)

    def lookup_items(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return self.lookup(
            order_id,
            fields={
                "order_id",
                "items",
            },
        )

    def lookup_membership(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return self.lookup(
            order_id,
            fields={
                "order_id",
                "membership_tier",
            },
        )

    def _apply_status_precedence(
        self,
        order: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Remove or neutralize stale shipping information when status
        makes that information misleading.

        The raw dataset may retain stale carrier/ETA/tracking values.
        """

        status = order.get("status")

        if status in {"cancelled", "returned"}:
            order = dict(order)

            order["carrier"] = None
            order["tracking_number"] = None
            order["estimated_delivery"] = None

        elif (
            status == "shipped"
            and order.get("estimated_delivery") is None
        ):
            # Deliberately keep the estimate as None.
            # Never calculate or invent a date.
            order = dict(order)

        return order

    @staticmethod
    def _safe_items(
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        safe_items = []

        for item in items:
            safe_items.append(
                {
                    key: item[key]
                    for key in OrderLookup.SAFE_ITEM_FIELDS
                    if key in item
                }
            )

        return safe_items

    def cancellation_window_status(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Determine whether an order is still inside the 30-minute
        cancellation window.

        This is a read-only calculation. It does NOT cancel anything.
        """

        order = self.lookup(
            order_id,
            fields={
                "order_id",
                "placed_at",
                "status",
            },
        )

        placed_at = self._parse_timestamp(
            order["placed_at"]
        )

        snapshot = self._parse_timestamp(
            self.snapshot_at
        )

        elapsed_seconds = (
            snapshot - placed_at
        ).total_seconds()

        remaining_seconds = max(
            0,
            (30 * 60) - elapsed_seconds,
        )

        within_window = (
            elapsed_seconds >= 0
            and elapsed_seconds <= 30 * 60
        )

        return {
            "order_id": order["order_id"],
            "status": order["status"],
            "within_30_minute_window": within_window,
            "remaining_seconds": int(remaining_seconds),
            "snapshot_at": self.snapshot_at,
        }

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)