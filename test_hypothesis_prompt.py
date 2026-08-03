import unittest

from ai.prompts import HYPOTHESIS_PROMPT


class HypothesisPromptTests(unittest.TestCase):
    def test_prompt_contains_required_json_contract_rules(self):
        self.assertIn("VALID JSON ONLY", HYPOTHESIS_PROMPT)
        self.assertIn("Create up to six active or research hypotheses", HYPOTHESIS_PROMPT)
        self.assertIn("Base every hypothesis on the supplied observations and journal context", HYPOTHESIS_PROMPT)
        self.assertIn("Do not speculate beyond the evidence", HYPOTHESIS_PROMPT)
        self.assertIn("Sentinel's rule: you own reasoning; Sentinel owns evidence", HYPOTHESIS_PROMPT)
        self.assertIn("Each hypothesis must be falsifiable", HYPOTHESIS_PROMPT)
        self.assertIn("Do not claim guaranteed profit", HYPOTHESIS_PROMPT)
        self.assertIn("Do not write disguised order instructions", HYPOTHESIS_PROMPT)
        self.assertIn('"hypotheses"', HYPOTHESIS_PROMPT)
        self.assertIn('"symbol"', HYPOTHESIS_PROMPT)
        self.assertIn('"title"', HYPOTHESIS_PROMPT)
        self.assertIn('"description"', HYPOTHESIS_PROMPT)
        self.assertIn('"source_observation_ids"', HYPOTHESIS_PROMPT)
        self.assertIn('"experiment_refs"', HYPOTHESIS_PROMPT)

    def test_prompt_supports_empty_result_when_insufficient_evidence(self):
        self.assertIn("If evidence is insufficient, return an empty hypotheses list", HYPOTHESIS_PROMPT)


if __name__ == "__main__":
    unittest.main()