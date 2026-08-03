import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

dotenv_module = ModuleType("dotenv")
dotenv_module.load_dotenv = lambda *_args, **_kwargs: None
sys.modules.setdefault("dotenv", dotenv_module)

openai_module = ModuleType("openai")
openai_module.OpenAI = object
sys.modules.setdefault("openai", openai_module)

from ai.journal import ResearchJournal
from ai.storage import Storage
from research.hypothesis import Hypothesis, HypothesisStatus
from research.observation import Observation
from research.parser import parse_observations


class FakeSnapshot:
    def __init__(self, symbol="NVDA", snapshot_date="2026-08-03"):
        self.symbol = symbol
        self.date = snapshot_date

    def to_text(self):
        return f"Symbol: {self.symbol}\nDate: {self.date}"


class ObservationPipelineTests(unittest.TestCase):
    def test_parser_returns_observation_objects(self):
        snapshot = FakeSnapshot()
        response = json.dumps(
            {
                "observations": [
                    {
                        "importance": 1,
                        "statement": "Close is above the configured 20-period SMA.",
                    }
                ]
            }
        )

        observations = parse_observations(
            snapshot,
            response,
            research_cycle_id="cycle-001",
            ai_call_id="ai-001",
            schema_version="1.0",
        )

        self.assertEqual(1, len(observations))
        self.assertIsInstance(observations[0], Observation)
        self.assertEqual("NVDA", observations[0].symbol_id)
        self.assertEqual("2026-08-03", observations[0].effective_time)
        self.assertEqual("cycle-001", observations[0].research_cycle_id)
        self.assertEqual("ai-001", observations[0].ai_call_id)
        self.assertEqual(["snapshot:NVDA:2026-08-03"], observations[0].evidence_refs)

    def test_storage_round_trip_and_append_only(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            first = Observation(
                observation_id="obs-1",
                symbol_id="NVDA",
                statement="First accepted observation.",
                evidence_refs=["snapshot:NVDA:2026-08-03"],
                importance=1,
                effective_time="2026-08-03",
                created_at="2026-08-03T00:00:00+00:00",
                research_cycle_id="cycle-001",
                ai_call_id="ai-001",
                schema_version="1.0",
            )

            second = Observation(
                observation_id="obs-2",
                symbol_id="NVDA",
                statement="Second accepted observation.",
                evidence_refs=["snapshot:NVDA:2026-08-03"],
                importance=2,
                effective_time="2026-08-03",
                created_at="2026-08-03T00:00:01+00:00",
                research_cycle_id="cycle-001",
                ai_call_id="ai-002",
                schema_version="1.0",
            )

            storage.save_observations("NVDA", [first])
            storage.save_observations("NVDA", [first, second])

            loaded = storage.load_observations("NVDA")

            self.assertEqual(2, len(loaded))
            self.assertTrue(all(isinstance(item, Observation) for item in loaded))
            self.assertEqual("First accepted observation.", loaded[0].statement)
            self.assertEqual("Second accepted observation.", loaded[1].statement)

    def test_journal_renders_observation_statement(self):
        journal = ResearchJournal()

        journal.storage = type(
            "FakeStorage",
            (),
            {
                "load_observations": staticmethod(
                    lambda _symbol: [
                        Observation(
                            observation_id="obs-1",
                            symbol_id="NVDA",
                            statement="Statement from observation pipeline.",
                            evidence_refs=["snapshot:NVDA:2026-08-03"],
                            importance=1,
                            effective_time="2026-08-03",
                            created_at="2026-08-03T00:00:00+00:00",
                            research_cycle_id="cycle-001",
                            ai_call_id="ai-001",
                            schema_version="1.0",
                        )
                    ]
                ),
                "load_hypotheses": staticmethod(
                    lambda _symbol: [
                        Hypothesis(
                            hypothesis_id="hyp-1",
                            symbol="NVDA",
                            title="Momentum continuation",
                            description="Price strength may continue after the breakout.",
                            status=HypothesisStatus.ACTIVE,
                            confidence=0.75,
                        )
                    ]
                ),
                "load_experiment_requests": staticmethod(lambda _symbol: []),
                "load_experiment_results": staticmethod(lambda _symbol: []),
            },
        )()

        result = journal.build("NVDA")

        self.assertIn("Statement from observation pipeline.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn("Momentum continuation", result)
        self.assertIn("[active]", result)
        self.assertIn("confidence=0.75", result)

    def test_journal_shows_empty_hypothesis_state(self):
        journal = ResearchJournal()

        journal.storage = type(
            "FakeStorage",
            (),
            {
                "load_observations": staticmethod(lambda _symbol: []),
                "load_hypotheses": staticmethod(lambda _symbol: []),
                "load_experiment_requests": staticmethod(lambda _symbol: []),
                "load_experiment_results": staticmethod(lambda _symbol: []),
            },
        )()

        result = journal.build("NVDA")

        self.assertIn("Observations", result)
        self.assertIn("No previous observations.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn("No active hypotheses.", result)

    def test_researcher_persists_observations(self):
        from ai.researcher import Researcher

        class FakeSentinel:
            def get_watchlist(self):
                return ["NVDA"]

            def get_snapshot(self, _symbol):
                return FakeSnapshot()

        class FakeAIClient:
            def observe(self, _snapshot):
                return json.dumps(
                    {
                        "observations": [
                            {
                                "importance": 1,
                                "statement": "Volume is above the prior configured baseline.",
                            }
                        ]
                    }
                )

        class FakeStorage:
            def __init__(self):
                self.saved_symbol = None
                self.saved_observations = []

            def save_observations(self, symbol, observations):
                self.saved_symbol = symbol
                self.saved_observations = observations

            def load_observations(self, _symbol):
                return []

            def load_hypotheses(self, _symbol):
                return []

            def load_experiment_requests(self, _symbol):
                return []

            def load_experiment_results(self, _symbol):
                return []

        class FakeHypothesisService:
            def __init__(self, *args, **kwargs):
                self.calls = []

            def generate_for_symbol(self, **kwargs):
                self.calls.append(kwargs)
                return []

        with patch("ai.researcher.AIClient", FakeAIClient), patch(
            "ai.researcher.Storage", FakeStorage
        ), patch(
            "ai.researcher.HypothesisService", FakeHypothesisService
        ), patch(
            "ai.researcher.ENABLE_HYPOTHESIS_GENERATION", False
        ):
            researcher = Researcher(FakeSentinel())
            researcher.research()

            self.assertEqual("NVDA", researcher.storage.saved_symbol)
            self.assertEqual(1, len(researcher.storage.saved_observations))
            self.assertIsInstance(researcher.storage.saved_observations[0], Observation)
            self.assertEqual(
                "Volume is above the prior configured baseline.",
                researcher.storage.saved_observations[0].statement,
            )
            self.assertEqual([], researcher.hypothesis_service.calls)

    def test_researcher_generates_hypotheses_when_enabled(self):
        from ai.researcher import Researcher

        class FakeSentinel:
            def get_watchlist(self):
                return ["NVDA"]

            def get_snapshot(self, _symbol):
                return FakeSnapshot()

        class FakeAIClient:
            def observe(self, _snapshot):
                return json.dumps(
                    {
                        "observations": [
                            {
                                "importance": 1,
                                "statement": "Volume is above the prior configured baseline.",
                            }
                        ]
                    }
                )

        class FakeStorage:
            def __init__(self):
                self.saved_symbol = None
                self.saved_observations = []

            def save_observations(self, symbol, observations):
                self.saved_symbol = symbol
                self.saved_observations = observations

            def load_observations(self, _symbol):
                return self.saved_observations

            def load_hypotheses(self, _symbol):
                return []

            def load_experiment_requests(self, _symbol):
                return []

            def load_experiment_results(self, _symbol):
                return []

        class FakeJournal:
            def __init__(self, *args, **kwargs):
                self.calls = []

            def build(self, symbol):
                self.calls.append(symbol)
                return f"Research Journal: {symbol}"

        class FakeHypothesisService:
            def __init__(self, *args, **kwargs):
                self.calls = []

            def generate_for_symbol(self, **kwargs):
                self.calls.append(kwargs)
                return ["hyp-1", "hyp-2"]

        with patch("ai.researcher.AIClient", FakeAIClient), patch(
            "ai.researcher.Storage", FakeStorage
        ), patch(
            "ai.researcher.ResearchJournal", FakeJournal
        ), patch(
            "ai.researcher.HypothesisService", FakeHypothesisService
        ), patch(
            "ai.researcher.ENABLE_HYPOTHESIS_GENERATION", True
        ):
            researcher = Researcher(FakeSentinel())
            researcher.research()

            self.assertEqual(["NVDA"], researcher.journal.calls)
            self.assertEqual(1, len(researcher.hypothesis_service.calls))

            call = researcher.hypothesis_service.calls[0]
            self.assertEqual("NVDA", call["symbol"])
            self.assertEqual("Research Journal: NVDA", call["journal"])
            self.assertEqual("Symbol: NVDA\nDate: 2026-08-03", call["snapshot_text"])
            self.assertEqual(1, len(call["observations"]))
            self.assertIsInstance(call["observations"][0], Observation)


if __name__ == "__main__":
    unittest.main()
