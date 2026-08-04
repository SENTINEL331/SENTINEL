import unittest
import sys
from types import ModuleType
from unittest.mock import patch

dotenv_module = ModuleType("dotenv")
dotenv_module.load_dotenv = lambda *_args, **_kwargs: None
sys.modules.setdefault("dotenv", dotenv_module)

openai_module = ModuleType("openai")
openai_module.OpenAI = object
sys.modules.setdefault("openai", openai_module)

from ai.client import AIClient
from ai.prompts import HYPOTHESIS_REVIEW_PROMPT, SYSTEM_PROMPT


class AIClientHypothesisReviewTests(unittest.TestCase):
    def test_hypothesis_review_method_delegates_to_chat_with_prompt(self):
        client = AIClient.__new__(AIClient)

        with patch.object(
            AIClient,
            "chat",
            return_value='{"hypothesis_reviews": []}',
        ) as mock_chat:
            result = client.hypothesis_review(
                symbol="NVDA",
                journal="Journal context.",
                hypotheses='[{"hypothesis_id": "hyp-001"}]',
            )

        self.assertEqual('{"hypothesis_reviews": []}', result)
        mock_chat.assert_called_once()

        system_prompt, user_prompt = mock_chat.call_args.args
        self.assertEqual(SYSTEM_PROMPT, system_prompt)
        self.assertIn(HYPOTHESIS_REVIEW_PROMPT.splitlines()[1].strip(), user_prompt)
        self.assertIn("Symbol: NVDA", user_prompt)
        self.assertIn("Journal Context:", user_prompt)
        self.assertIn("Journal context.", user_prompt)
        self.assertIn('[{"hypothesis_id": "hyp-001"}]', user_prompt)

    def test_hypothesis_review_method_uses_chat_output_verbatim(self):
        client = AIClient.__new__(AIClient)

        with patch.object(AIClient, "chat", return_value="raw-json-text") as mock_chat:
            result = client.hypothesis_review(
                symbol="NVDA",
                journal="Journal context.",
                hypotheses="[]",
            )

        self.assertEqual("raw-json-text", result)
        mock_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()
