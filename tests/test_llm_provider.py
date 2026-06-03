import asyncio
import unittest

import httpx
from groq import RateLimitError as GroqRateLimitError

from utils.llm import (
    LLMClientProvider,
    LLMProviderConfig,
    ainvoke_with_backoff,
    get_llm,
    set_llm_model,
    use_llm_provider,
)


class LlmProviderTests(unittest.TestCase):
    def test_provider_resolves_default_and_node_model_overrides(self):
        calls = []

        def fake_factory(provider, model, node_name):
            calls.append((provider, model, node_name))
            return {"provider": provider, "model": model, "node_name": node_name}

        provider = LLMClientProvider(
            LLMProviderConfig(
                provider="groq",
                default_model="llama-default",
                node_models={"parser_agent": "llama-parser"},
            ),
            client_factory=fake_factory,
        )

        with use_llm_provider(provider):
            self.assertEqual(get_llm("schemaInference")["model"], "llama-default")
            self.assertEqual(get_llm("parser_agent")["model"], "llama-parser")
            self.assertIs(get_llm("parser_agent"), get_llm("parser_agent"))

        self.assertEqual(
            calls,
            [
                ("groq", "llama-default", "schemaInference"),
                ("groq", "llama-parser", "parser_agent"),
            ],
        )

    def test_set_llm_model_preserves_openai_default_compatibility(self):
        provider = set_llm_model("gpt-test")

        self.assertEqual(provider.provider, "openai")
        self.assertEqual(provider.default_model, "gpt-test")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            LLMProviderConfig(provider="unknown", default_model="model")

    def test_groq_rate_limit_errors_are_retried(self):
        class FlakyRunnable:
            def __init__(self):
                self.attempts = 0

            async def ainvoke(self, *args, **kwargs):
                self.attempts += 1
                if self.attempts == 1:
                    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
                    response = httpx.Response(429, request=request)
                    raise GroqRateLimitError("rate limited", response=response, body=None)
                return "ok"

        runnable = FlakyRunnable()

        result = asyncio.run(
            ainvoke_with_backoff(
                runnable,
                max_retries=1,
                base_delay=0,
                jitter=0,
            )
        )

        self.assertEqual(result, "ok")
        self.assertEqual(runnable.attempts, 2)


if __name__ == "__main__":
    unittest.main()
