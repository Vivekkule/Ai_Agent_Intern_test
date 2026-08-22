from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ConversationMemory:
    """
    Stores the conversation for a single support session.

    The memory is intentionally simple and explicit. We don't want
    hidden state or uncontrolled accumulation.
    """

    max_messages: int = 20
    messages: list[Message] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        self._add("user", content)

    def add_assistant_message(self, content: str) -> None:
        self._add("assistant", content)

    def _add(self, role: str, content: str) -> None:
        self.messages.append(
            Message(
                role=role,
                content=content,
            )
        )

        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_messages(self) -> list[dict[str, str]]:
        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]

    def clear(self) -> None:
        self.messages.clear()

    def last_user_message(self) -> str | None:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content

        return None

    def last_assistant_message(self) -> str | None:
        for message in reversed(self.messages):
            if message.role == "assistant":
                return message.content

        return None