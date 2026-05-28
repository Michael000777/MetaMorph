import unittest

from metamorph.validation_contracts import validate_transformation_contract


class TransformationContractTests(unittest.TestCase):
    def test_valid_single_output_column(self):
        result = validate_transformation_contract(
            raw_values=["5 ft 10 in", "170 cm"],
            transformed_values=[[177.8, 170.0]],
            output_names=["height_cm"],
            confidence=0.99,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.issues, [])

    def test_valid_multi_output_column(self):
        result = validate_transformation_contract(
            raw_values=["2024-01-12", "unknown"],
            transformed_values=[["2024-01-12", None], [2024, None]],
            output_names=["date_iso", "year"],
            confidence=0.9,
        )

        self.assertTrue(result.passed)

    def test_row_major_shape_is_detected(self):
        result = validate_transformation_contract(
            raw_values=["5 ft 10 in", "170 cm"],
            transformed_values=[[177.8], [170.0]],
            output_names=["height_cm"],
            confidence=0.9,
        )

        self.assertFalse(result.passed)
        self.assertIn("row_major_orientation", [issue.category for issue in result.issues])
        self.assertEqual(result.failed_rows, [0, 1])

    def test_row_length_mismatch_is_detected(self):
        result = validate_transformation_contract(
            raw_values=["a", "b", "c"],
            transformed_values=[["a", "b"]],
            output_names=["cleaned"],
            confidence=0.8,
        )

        self.assertFalse(result.passed)
        self.assertIn("row_length_mismatch", [issue.category for issue in result.issues])
        self.assertEqual(result.failed_rows, [2])

    def test_invalid_scalar_is_detected(self):
        result = validate_transformation_contract(
            raw_values=["a", "b"],
            transformed_values=[["a", {"bad": "value"}]],
            output_names=["cleaned"],
            confidence=0.8,
        )

        self.assertFalse(result.passed)
        self.assertIn("invalid_scalar", [issue.category for issue in result.issues])
        self.assertEqual(result.failed_rows, [1])

    def test_output_name_mismatch_is_detected(self):
        result = validate_transformation_contract(
            raw_values=["a", "b"],
            transformed_values=[["a", "b"], [1, 2]],
            output_names=["cleaned"],
            confidence=0.8,
        )

        self.assertFalse(result.passed)
        self.assertIn("output_name_mismatch", [issue.category for issue in result.issues])

    def test_invalid_confidence_is_detected(self):
        result = validate_transformation_contract(
            raw_values=["a"],
            transformed_values=[["a"]],
            output_names=["cleaned"],
            confidence=1.2,
        )

        self.assertFalse(result.passed)
        self.assertIn("invalid_confidence", [issue.category for issue in result.issues])


if __name__ == "__main__":
    unittest.main()
