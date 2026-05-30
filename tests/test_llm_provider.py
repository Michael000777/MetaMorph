import unittest

from utils.llm import (
    LLMClientProvider,
    LLMProviderConfig,
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


if __name__ == "__main__":
    unittest.main()
