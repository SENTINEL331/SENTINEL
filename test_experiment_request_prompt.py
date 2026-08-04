import unittest

from ai.prompts import EXPERIMENT_REQUEST_PROMPT


class ExperimentRequestPromptTests(unittest.TestCase):
    def test_prompt_contains_required_json_contract_rules(self):
        self.assertIn("VALID JSON ONLY", EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("Convert eligible hypotheses into testable experiment requests", EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("Sentinel executes tests; you only propose structured Experiment Requests", EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("do not execute any experiment", EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("Do not claim that you ran a backtest, validation, or paper trade", EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("If no hypothesis is ready for testing, return an empty experiment_requests list", EXPERIMENT_REQUEST_PROMPT)

        self.assertIn('"experiment_requests"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"experiment_request_id"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"hypothesis_id"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"hypothesis_version_id"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"symbol"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"title"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"objective"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"test_type"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"entry_conditions"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"machine_readable_entry_conditions"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"exit_conditions"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"time_horizon"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"forward_horizon"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"status"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"source_observation_ids"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"created_at"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn('"updated_at"', EXPERIMENT_REQUEST_PROMPT)
        self.assertIn("condition evaluator", EXPERIMENT_REQUEST_PROMPT)

    def test_prompt_formats_without_treating_json_examples_as_placeholders(self):
        formatted = EXPERIMENT_REQUEST_PROMPT.format(
            hypotheses="[]",
            journal="journal",
            observations="[]",
        )

        self.assertIn('{"field": "Close", "operator": ">", "value": 100.0}', formatted)
        self.assertIn('{"field": "Close", "operator": ">", "other_field": "EMA_20"}', formatted)


if __name__ == "__main__":
    unittest.main()