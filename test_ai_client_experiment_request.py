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
from ai.prompts import EXPERIMENT_REQUEST_PROMPT, SYSTEM_PROMPT


class AIClientExperimentRequestTests(unittest.TestCase):
    def test_experiment_request_method_delegates_to_chat_with_prompt(self):
        client = AIClient.__new__(AIClient)

        with patch.object(
            AIClient,
            "chat",
            return_value='{"experiment_requests": []}',
        ) as mock_chat:
            result = client.experiment_request(
                symbol="NVDA",
                journal="Journal notes go here.",
                hypotheses='[{"hypothesis_id": "hyp-001"}]',
                observations='[{"observation_id": "obs-1"}]',
            )

        self.assertEqual('{"experiment_requests": []}', result)
        mock_chat.assert_called_once()

        system_prompt, user_prompt = mock_chat.call_args.args
        self.assertEqual(SYSTEM_PROMPT, system_prompt)
        self.assertIn(EXPERIMENT_REQUEST_PROMPT.splitlines()[1].strip(), user_prompt)
        self.assertIn("Symbol: NVDA", user_prompt)
        self.assertIn("Journal Context:", user_prompt)
        self.assertIn("Journal notes go here.", user_prompt)
        self.assertIn('[{"hypothesis_id": "hyp-001"}]', user_prompt)
        self.assertIn('[{"observation_id": "obs-1"}]', user_prompt)

    def test_experiment_request_method_uses_chat_output_verbatim(self):
        client = AIClient.__new__(AIClient)

        with patch.object(AIClient, "chat", return_value="raw-json-text") as mock_chat:
            result = client.experiment_request(
                symbol="NVDA",
                journal="Journal notes go here.",
                hypotheses="[]",
            )

        self.assertEqual("raw-json-text", result)
        mock_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()