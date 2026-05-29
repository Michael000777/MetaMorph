import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langgraph.graph import END

from metamorph import validator
from utils.MetaMorphState import (
    InputColumnData,
    MetaMorphState,
    ColSample,
    RefinementResults,
    ValidatorData,
    parsedData,
)


class FakeLlm:
    def with_structured_output(self, *args, **kwargs):
        return self


def make_state(
    *,
    raw_values=None,
    transformed_values=None,
    output_names=None,
    retry_count=0,
):
    raw_values = raw_values if raw_values is not None else ["a", "b"]
    transformed_values = transformed_values if transformed_values is not None else [["a", "b"]]
    output_names = output_names if output_names is not None else ["cleaned"]

    state = MetaMorphState(
        input_column_data=InputColumnData(column_name="sample", values=raw_values),
        ColumnSample=ColSample(column_name="sample", row_count=len(raw_values)),
        parsed_data_output=parsedData(
            column_name={"sample": output_names},
            parsed_output=transformed_values,
            model_confidence=0.9,
        ),
        refinement_results=RefinementResults(
            cleaned_values=transformed_values,
            confidence=0.9,
            refinement_attempts=1,
        ),
    )
    if retry_count:
        state.validator_data = ValidatorData(
            passed=False,
            failed_rows=[],
            retry_count=retry_count,
            message="previous retry",
            status="recoverable_retry",
            final_route="refinement_agent",
        )
    return state


class ValidatorFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_validator_pass_ends_graph(self):
        llm_result = SimpleNamespace(
            decision="pass",
            reason="looks valid",
            confidence=0.95,
            failed_rows_indices=[],
        )

        with (
            patch.object(validator, "get_llm", return_value=FakeLlm()),
            patch.object(validator, "ainvoke_with_backoff", return_value=llm_result),
        ):
            result = await validator.validator_node(make_state())

        self.assertEqual(result.goto, END)
        validator_data = result.update["validator_data"]
        self.assertTrue(validator_data.passed)
        self.assertEqual(validator_data.status, "pass")
        self.assertEqual(validator_data.retry_count, 0)
        self.assertEqual(validator_data.final_route, END)

    async def test_validator_retry_then_pass_preserves_retry_count(self):
        retry_result = await validator.validator_node(
            make_state(transformed_values=[["a"]])
        )

        self.assertEqual(retry_result.goto, "refinement_agent")
        retry_data = retry_result.update["validator_data"]
        self.assertFalse(retry_data.passed)
        self.assertEqual(retry_data.status, "recoverable_retry")
        self.assertEqual(retry_data.retry_count, 1)
        self.assertEqual(retry_data.failed_rows, [1])

        llm_result = SimpleNamespace(
            decision="pass",
            reason="fixed",
            confidence=0.95,
            failed_rows_indices=[],
        )
        passing_state = make_state(retry_count=retry_data.retry_count)

        with (
            patch.object(validator, "get_llm", return_value=FakeLlm()),
            patch.object(validator, "ainvoke_with_backoff", return_value=llm_result),
        ):
            pass_result = await validator.validator_node(passing_state)

        pass_data = pass_result.update["validator_data"]
        self.assertEqual(pass_result.goto, END)
        self.assertTrue(pass_data.passed)
        self.assertEqual(pass_data.status, "pass")
        self.assertEqual(pass_data.retry_count, 1)

    async def test_validator_retry_exhaustion_ends_graph(self):
        result = await validator.validator_node(
            make_state(
                transformed_values=[["a"]],
                retry_count=validator.MAX_RETRIES,
            )
        )

        self.assertEqual(result.goto, END)
        validator_data = result.update["validator_data"]
        self.assertFalse(validator_data.passed)
        self.assertEqual(validator_data.status, "terminal_fail")
        self.assertEqual(validator_data.retry_count, validator.MAX_RETRIES)
        self.assertEqual(validator_data.final_route, END)

    async def test_validator_terminal_fail_ends_graph(self):
        llm_result = SimpleNamespace(
            decision="fail",
            reason="semantic mismatch",
            confidence=0.8,
            failed_rows_indices=[0],
        )

        with (
            patch.object(validator, "get_llm", return_value=FakeLlm()),
            patch.object(validator, "ainvoke_with_backoff", return_value=llm_result),
        ):
            result = await validator.validator_node(make_state())

        self.assertEqual(result.goto, END)
        validator_data = result.update["validator_data"]
        self.assertFalse(validator_data.passed)
        self.assertEqual(validator_data.status, "terminal_fail")
        self.assertEqual(validator_data.message, "semantic mismatch")
        self.assertEqual(validator_data.failed_rows, [0])


if __name__ == "__main__":
    unittest.main()
