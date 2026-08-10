import sys
import unittest
from types import ModuleType
from unittest.mock import patch

dotenv_module = ModuleType("dotenv")
dotenv_module.load_dotenv = lambda *_args, **_kwargs: None
sys.modules.setdefault("dotenv", dotenv_module)

openai_module = ModuleType("openai")
openai_module.OpenAI = object
sys.modules.setdefault("openai", openai_module)

from ai.client import AIClient
from ai.prompts import DEMO_TRADE_CANDIDATE_PROMPT, SYSTEM_PROMPT


class AIClientDemoTradeCandidateGenerationTests(unittest.TestCase):
    def test_method_delegates_to_chat_with_prompt(self):
        client = AIClient.__new__(AIClient)

        with patch.object(
            AIClient,
            "chat",
            return_value='{"demo_trade_candidates": []}',
        ) as mock_chat:
            result = client.demo_trade_candidate_generation(
                symbol="NVDA",
                journal="Journal context.",
                qualified_candidates='[{"source_hypothesis_id": "hyp-001"}]',
            )

        self.assertEqual('{"demo_trade_candidates": []}', result)
        mock_chat.assert_called_once()

        system_prompt, user_prompt = mock_chat.call_args.args
        self.assertEqual(SYSTEM_PROMPT, system_prompt)
        self.assertIn(DEMO_TRADE_CANDIDATE_PROMPT.splitlines()[1].strip(), user_prompt)
        self.assertIn("Symbol: NVDA", user_prompt)
        self.assertIn("Journal Context:", user_prompt)
        self.assertIn("Journal context.", user_prompt)
        self.assertIn('[{"source_hypothesis_id": "hyp-001"}]', user_prompt)


if __name__ == "__main__":
    unittest.main()