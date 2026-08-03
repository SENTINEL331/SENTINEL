import unittest

from research.condition_evaluator import evaluate_condition


class ConditionEvaluatorTests(unittest.TestCase):
    def test_numeric_field_to_value_comparisons(self):
        row = {
            "Close": 195.5,
            "EMA_20": 200.0,
            "RSI_14": 62.0,
        }

        self.assertTrue(
            evaluate_condition(
                {"field": "Close", "operator": "<", "value": 200},
                row,
            )
        )
        self.assertTrue(
            evaluate_condition(
                {"field": "Close", "operator": "<=", "value": 195.5},
                row,
            )
        )
        self.assertTrue(
            evaluate_condition(
                {"field": "RSI_14", "operator": ">", "value": 50},
                row,
            )
        )
        self.assertTrue(
            evaluate_condition(
                {"field": "Close", "operator": ">=", "value": 195.5},
                row,
            )
        )
        self.assertTrue(
            evaluate_condition(
                {"field": "RSI_14", "operator": "!=", "value": 70},
                row,
            )
        )

    def test_field_to_field_comparisons(self):
        row = {
            "Close": 195.5,
            "EMA_20": 200.0,
            "SMA_50": 195.5,
        }

        self.assertTrue(
            evaluate_condition(
                {
                    "field": "Close",
                    "operator": "<",
                    "other_field": "EMA_20",
                },
                row,
            )
        )
        self.assertTrue(
            evaluate_condition(
                {
                    "field": "Close",
                    "operator": "==",
                    "other_field": "SMA_50",
                },
                row,
            )
        )

    def test_unknown_field_raises_clear_error(self):
        row = {"Close": 195.5}

        with self.assertRaisesRegex(ValueError, "unknown field: VWAP"):
            evaluate_condition(
                {"field": "VWAP", "operator": "<", "value": 200},
                row,
            )

    def test_unknown_other_field_raises_clear_error(self):
        row = {"Close": 195.5}

        with self.assertRaisesRegex(ValueError, "unknown field: EMA_20"):
            evaluate_condition(
                {
                    "field": "Close",
                    "operator": "<",
                    "other_field": "EMA_20",
                },
                row,
            )

    def test_unsupported_operator_raises_clear_error(self):
        row = {"Close": 195.5}

        with self.assertRaisesRegex(ValueError, "unsupported operator"):
            evaluate_condition(
                {"field": "Close", "operator": "contains", "value": 200},
                row,
            )

    def test_malformed_condition_raises_clear_error(self):
        row = {"Close": 195.5, "EMA_20": 200.0}

        with self.assertRaisesRegex(
            ValueError,
            "condition must include exactly one of 'value' or 'other_field'",
        ):
            evaluate_condition(
                {
                    "field": "Close",
                    "operator": "<",
                    "value": 200,
                    "other_field": "EMA_20",
                },
                row,
            )

        with self.assertRaisesRegex(
            ValueError,
            "condition must include exactly one of 'value' or 'other_field'",
        ):
            evaluate_condition(
                {"field": "Close", "operator": "<"},
                row,
            )

    def test_non_numeric_inequality_inputs_raise_clear_error(self):
        row = {
            "Close": "195.5",
            "EMA_20": 200.0,
        }

        with self.assertRaisesRegex(ValueError, "must be numeric"):
            evaluate_condition(
                {"field": "Close", "operator": "<", "value": 200},
                row,
            )

        with self.assertRaisesRegex(ValueError, "must be numeric"):
            evaluate_condition(
                {"field": "EMA_20", "operator": ">", "value": "199"},
                row,
            )


if __name__ == "__main__":
    unittest.main()