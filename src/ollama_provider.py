from __future__ import annotations

from ollama import chat


class OllamaProvider:
    """
    LLMProvider implementation using a local Ollama model.
    """

    def __init__(
        self,
        model: str = "llama3.1:latest",
    ):
        self.model = model

    def generate(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        response = chat(
            model=self.model,
            messages=messages,
        )

        return response["message"]["content"]