import unittest
from unittest.mock import patch

from langgraph.graph import END

from metamorph import schema_inference, supervisor, validator
from utils.MetaMorphState import (
    ColSample,
    InputColumnData,
    MetaMorphState,
    parsedData,
    RefinementResults,
    ValidatorData,
)
from utils.prompts import load_prompts


class FakeLLM:
    def __init__(self):
        self.structured_calls = []

    def with_structured_output(self, schema, **kwargs):
        self.structured_calls.append((schema, kwargs))
        return {"schema": schema, "kwargs": kwargs}


class PromptContractTextTests(unittest.TestCase):
    def setUp(self):
        self.prompts = load_prompts()

    def test_supervisor_prompt_matches_schema_fields(self):
        prompt = self.prompts["Supervisor_system_prompt"]

        self.assertIn('"next"', prompt)
        self.assertIn('"justification"', prompt)
        self.assertIn("Required fields", prompt)
        self.assertIn("schemaInference", prompt)
        self.assertIn("parser_agent", prompt)
        self.assertIn("refinement_agent", prompt)
        self.assertIn("validator_agent", prompt)

    def test_schema_inference_prompt_matches_schema_fields(self):
        prompt = self.prompts["schema_inference_prompt"]

        self.assertIn('"Inferred_type"', prompt)
        self.assertIn('"conf"', prompt)
        self.assertIn('"reason"', prompt)
        self.assertIn("Required fields", prompt)

    def test_parser_and_refinement_prompts_match_schema_fields(self):
        parser_prompt = self.prompts["parser_prompt"]
        refinement_prompt = self.prompts["refinement_prompt"]

        for field in ("column", "parsed_col_data", "confidence", "notes"):
            self.assertIn(field, parser_prompt)

        for field in ("refined_values", "confidence", "notes"):
            self.assertIn(field, refinement_prompt)

    def test_validator_prompt_matches_schema_fields(self):
        prompt = self.prompts["validator_prompt"]

        self.assertIn('"decision"', prompt)
        self.assertIn('"reason"', prompt)
        self.assertIn('"confidence"', prompt)
        self.assertIn('"failed_rows_indices"', prompt)
        self.assertIn('"pass" | "retry" | "fail"', prompt)
        self.assertIn("zero-based row indices", prompt)


class StructuredOutputNodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_supervisor_node_uses_structured_schema_and_records_justification(self):
        fake_llm = FakeLLM()
        state = MetaMorphState(
            input_column_data=InputColumnData(column_name="height", values=["5 ft 10 in"]),
            ColumnSample=ColSample(column_name="height", row_count=1),
        )
        response = supervisor.Supervisor(
            next="schemaInference",
            justification="Schema has not been inferred yet.",
        )

        async def fake_ainvoke(runnable, messages):
            self.assertEqual(runnable["schema"], supervisor.Supervisor)
            self.assertTrue(any("justification" in m["content"] for m in messages))
            return response

        with (
            patch.object(supervisor, "get_llm", return_value=fake_llm),
            patch.object(supervisor, "ainvoke_with_backoff", side_effect=fake_ainvoke),
        ):
            command = await supervisor.supervisor_node(state)

        self.assertEqual(fake_llm.structured_calls[0][0], supervisor.Supervisor)
        self.assertEqual(command.goto, "schemaInference")
        node_path = command.update["Node_Col_Tracker"]["node_path"]["height"]
        self.assertIn("Schema has not been inferred yet.", node_path.values())

    async def test_schema_inference_node_uses_structured_schema_fields(self):
        fake_llm = FakeLLM()
        state = MetaMorphState(
            input_column_data=InputColumnData(column_name="height", values=["170 cm"]),
            ColumnSample=ColSample(
                column_name="height",
                head=["170 cm"],
                tail=["170 cm"],
                random_sample=[],
                n_unique_preview=1,
                unique_preview=["170 cm"],
                row_count=1,
            ),
        )
        response = schema_inference.SchemaInference(
            Inferred_type="height",
            conf=0.95,
            reason="Values look like human heights with units.",
        )

        async def fake_ainvoke(runnable, messages):
            self.assertEqual(runnable["schema"], schema_inference.SchemaInference)
            self.assertTrue(any("Inferred_type" in m["content"] for m in messages))
            return response

        with (
            patch.object(schema_inference, "get_llm", return_value=fake_llm),
            patch.object(schema_inference, "ainvoke_with_backoff", side_effect=fake_ainvoke),
        ):
            command = await schema_inference.schema_inference_node(state)

        self.assertEqual(fake_llm.structured_calls[0][0], schema_inference.SchemaInference)
        self.assertEqual(command.goto, "supervisor")
        self.assertEqual(command.update["schema_inference"]["inferred_type"], "height")
        self.assertEqual(command.update["schema_inference"]["confidence"], 0.95)
        self.assertEqual(
            command.update["schema_inference"]["notes"],
            "Values look like human heights with units.",
        )

    async def test_validator_node_uses_structured_schema_and_preserves_reason(self):
        fake_llm = FakeLLM()
        state = MetaMorphState(
            input_column_data=InputColumnData(column_name="height", values=["170 cm"]),
            ColumnSample=ColSample(column_name="height", row_count=1),
            refinement_results=RefinementResults(
                cleaned_values=[[170]],
                confidence=0.98,
                refinement_attempts=1,
            ),
        )
        response = validator.ValidatorLLMOutput(
            decision="pass",
            reason="Output is row-aligned and plausible.",
            confidence=0.96,
            failed_rows_indices=[],
        )

        async def fake_ainvoke(runnable, messages):
            self.assertEqual(runnable["schema"], validator.ValidatorLLMOutput)
            self.assertTrue(any("failed_rows_indices" in m["content"] for m in messages))
            return response

        with (
            patch.object(validator, "get_llm", return_value=fake_llm),
            patch.object(validator, "ainvoke_with_backoff", side_effect=fake_ainvoke),
        ):
            command = await validator.validator_node(state)

        self.assertEqual(fake_llm.structured_calls[0][0], validator.ValidatorLLMOutput)
        self.assertEqual(command.goto, END)
        self.assertTrue(command.update["validator_data"].passed)
        self.assertEqual(command.update["validator_data"].message, "Output is row-aligned and plausible.")
        self.assertEqual(command.update["validator_data"].failed_rows, [])

    async def test_validator_node_retries_contract_failure_without_llm(self):
        state = MetaMorphState(
            input_column_data=InputColumnData(column_name="height", values=["5 ft 10 in", "170 cm"]),
            ColumnSample=ColSample(column_name="height", row_count=2),
            parsed_data_output=parsedData(column_name={"height": ["height_cm"]}),
            refinement_results=RefinementResults(
                cleaned_values=[[177.8], [170.0]],
                confidence=0.98,
                refinement_attempts=1,
            ),
        )

        with patch.object(validator, "get_llm", side_effect=AssertionError("LLM should not be called")):
            command = await validator.validator_node(state)

        self.assertEqual(command.goto, "refinement_agent")
        self.assertFalse(command.update["validator_data"].passed)
        self.assertEqual(command.update["validator_data"].retry_count, 1)
        self.assertEqual(command.update["validator_data"].failed_rows, [0, 1])
        self.assertIn("row_major_orientation", command.update["validator_data"].message)

    async def test_validator_node_routes_exhausted_contract_failure_to_supervisor(self):
        state = MetaMorphState(
            input_column_data=InputColumnData(column_name="height", values=["5 ft 10 in", "170 cm"]),
            ColumnSample=ColSample(column_name="height", row_count=2),
            parsed_data_output=parsedData(column_name={"height": ["height_cm"]}),
            refinement_results=RefinementResults(
                cleaned_values=[[177.8]],
                confidence=0.98,
                refinement_attempts=6,
            ),
            validator_data=ValidatorData(
                passed=False,
                failed_rows=[1],
                retry_count=validator.MAX_RETRIES,
                message="Previous retry",
            ),
        )

        with patch.object(validator, "get_llm", side_effect=AssertionError("LLM should not be called")):
            command = await validator.validator_node(state)

        self.assertEqual(command.goto, "supervisor")
        self.assertFalse(command.update["validator_data"].passed)
        self.assertEqual(command.update["validator_data"].retry_count, validator.MAX_RETRIES)
        self.assertIn("row_length_mismatch", command.update["validator_data"].message)


if __name__ == "__main__":
    unittest.main()
