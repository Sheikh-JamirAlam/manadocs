from __future__ import annotations

from typing import Any, Protocol, Type

from langchain_google_genai import ChatGoogleGenerativeAI


class StructuredModelProvider(Protocol):
    def structured(self, model: str, schema: Type[Any]) -> Any:
        """Return a structured-output model for a graph node."""


class GeminiModelProvider:
    def structured(self, model: str, schema: Type[Any]) -> Any:
        return ChatGoogleGenerativeAI(model=model).with_structured_output(schema)


_provider: StructuredModelProvider = GeminiModelProvider()


def get_structured_model(model: str, schema: Type[Any]) -> Any:
    return _provider.structured(model, schema)


def set_model_provider(provider: StructuredModelProvider) -> None:
    global _provider
    _provider = provider
