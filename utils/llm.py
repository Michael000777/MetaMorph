from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable, Mapping
import random

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import APIError, APITimeoutError, RateLimitError

load_dotenv()

SUPPORTED_PROVIDERS = {"openai", "groq"}


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str = "openai"
    default_model: str = "gpt-5-nano"
    node_models: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        provider = self.provider.lower()
        if provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported LLM provider '{self.provider}'. Supported providers: {supported}.")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "node_models", dict(self.node_models or {}))


LLMClientFactory = Callable[[str, str, str | None], object]


class LLMClientProvider:
    def __init__(
        self,
        config: LLMProviderConfig,
        client_factory: LLMClientFactory | None = None,
    ):
        self.config = config
        self._client_factory = client_factory
        self._clients: dict[tuple[str, str], object] = {}

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def default_model(self) -> str:
        return self.config.default_model

    def resolve_model(self, node_name: str | None = None) -> str:
        if node_name and node_name in self.config.node_models:
            return self.config.node_models[node_name]
        return self.config.default_model

    def get_llm(self, node_name: str | None = None):
        model = self.resolve_model(node_name)
        key = (self.config.provider, model)
        if key not in self._clients:
            if self._client_factory:
                self._clients[key] = self._client_factory(self.config.provider, model, node_name)
            else:
                self._clients[key] = build_llm_client(self.config.provider, model)
        return self._clients[key]


def build_llm_client(provider: str, model: str):
    provider = provider.lower()
    if provider == "openai":
        return ChatOpenAI(model=model)
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=model)
    supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
    raise ValueError(f"Unsupported LLM provider '{provider}'. Supported providers: {supported}.")


_CURRENT_PROVIDER: ContextVar[LLMClientProvider | None] = ContextVar("metamorph_llm_provider", default=None)
_GLOBAL_PROVIDER: LLMClientProvider | None = None


def set_llm_provider(
    provider: str = "openai",
    model: str = "gpt-5-nano",
    node_models: Mapping[str, str] | None = None,
) -> LLMClientProvider:
    global _GLOBAL_PROVIDER
    _GLOBAL_PROVIDER = LLMClientProvider(
        LLMProviderConfig(
            provider=provider,
            default_model=model,
            node_models=node_models or {},
        )
    )
    return _GLOBAL_PROVIDER


def set_llm_model(model_name: str):
    return set_llm_provider(provider="openai", model=model_name)


@contextmanager
def use_llm_provider(provider: LLMClientProvider):
    token = _CURRENT_PROVIDER.set(provider)
    try:
        yield provider
    finally:
        _CURRENT_PROVIDER.reset(token)


def get_llm_provider() -> LLMClientProvider:
    provider = _CURRENT_PROVIDER.get() or _GLOBAL_PROVIDER
    if provider is None:
        raise ValueError("LLM provider not set. Configure one before calling get_llm().")
    return provider


def get_llm(node_name: str | None = None):
    return get_llm_provider().get_llm(node_name=node_name)


async def ainvoke_with_backoff(runnable, *args, max_retries=8, base_delay=0.5, max_delay=10.0, jitter=0.2, **kwargs):
    """
    runnable: In this case our llm api call with .ainvoke()
    """
    for attempt in range(max_retries + 1):
        try:
            return await runnable.ainvoke(*args, **kwargs)
        except RateLimitError:
            if attempt == max_retries:
                raise

            delay = min(max_delay, base_delay * (2 ** attempt))
            delay = delay + random.uniform(0, jitter)
            await asyncio.sleep(delay)

        except (APITimeoutError, APIError):
            if attempt == max_retries:
                raise

            delay = min(max_delay, base_delay * (2 ** attempt))
            delay = delay + random.uniform(0, jitter)
            await asyncio.sleep(delay)
