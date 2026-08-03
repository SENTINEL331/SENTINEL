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
from ai.prompts import HYPOTHESIS_PROMPT, SYSTEM_PROMPT


class AIClientHypothesisTests(unittest.TestCase):
    def test_hypothesis_method_delegates_to_chat_with_hypothesis_prompt(self):
        client = AIClient.__new__(AIClient)

        with patch.object(
            AIClient,
            "chat",
            return_value='{"hypotheses": []}',
        ) as mock_chat:
            result = client.hypothesis(
                symbol="NVDA",
                journal="Journal notes go here.",
                observations='[{"statement": "Observation text."}]',
                snapshot_text="Snapshot text goes here.",
            )

        self.assertEqual('{"hypotheses": []}', result)
        mock_chat.assert_called_once()

        system_prompt, user_prompt = mock_chat.call_args.args
        self.assertEqual(SYSTEM_PROMPT, system_prompt)
        self.assertIn(HYPOTHESIS_PROMPT.splitlines()[1].strip(), user_prompt)
        self.assertIn("Symbol: NVDA", user_prompt)
        self.assertIn("Journal Context:", user_prompt)
        self.assertIn("Journal notes go here.", user_prompt)
        self.assertIn("Snapshot Evidence:", user_prompt)
        self.assertIn("Snapshot text goes here.", user_prompt)
        self.assertIn('[{"statement": "Observation text."}]', user_prompt)

    def test_hypothesis_method_uses_chat_output_verbatim(self):
        client = AIClient.__new__(AIClient)

        with patch.object(AIClient, "chat", return_value="raw-json-text") as mock_chat:
            result = client.hypothesis(
                symbol="NVDA",
                journal="Journal notes go here.",
                observations="[]",
            )

        self.assertEqual("raw-json-text", result)
        mock_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()