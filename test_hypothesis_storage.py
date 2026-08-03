import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.hypothesis import Hypothesis, HypothesisStatus


class HypothesisStorageTests(unittest.TestCase):
    def test_save_and_load_hypotheses_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
            updated_at = datetime(2026, 8, 3, 0, 15, tzinfo=timezone.utc)

            hypothesis = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.75,
                source_observation_ids=("obs-1", "obs-2"),
                parent_hypothesis_id="hyp-root",
                lineage_hypothesis_ids=("hyp-root", "hyp-parent"),
                experiment_refs=("exp-1", "exp-2"),
                created_at=created_at,
                updated_at=updated_at,
            )

            storage.save_hypotheses("NVDA", [hypothesis])

            loaded = storage.load_hypotheses("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], Hypothesis)
            self.assertEqual("hyp-001", loaded[0].hypothesis_id)
            self.assertEqual("NVDA", loaded[0].symbol)
            self.assertEqual("Momentum continuation", loaded[0].title)
            self.assertEqual(
                "Price strength may continue after an earnings-driven breakout.",
                loaded[0].description,
            )
            self.assertEqual(HypothesisStatus.ACTIVE, loaded[0].status)
            self.assertEqual(0.75, loaded[0].confidence)
            self.assertEqual(("obs-1", "obs-2"), loaded[0].source_observation_ids)
            self.assertEqual("hyp-root", loaded[0].parent_hypothesis_id)
            self.assertEqual(("hyp-root", "hyp-parent"), loaded[0].lineage_hypothesis_ids)
            self.assertEqual(("exp-1", "exp-2"), loaded[0].experiment_refs)
            self.assertEqual(created_at, loaded[0].created_at)
            self.assertEqual(updated_at, loaded[0].updated_at)

            hypotheses_file = Path(tmp_dir) / "hypotheses" / "NVDA.json"
            self.assertTrue(hypotheses_file.exists())

    def test_save_hypotheses_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

            first = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                created_at=created_at,
                updated_at=created_at,
            )

            duplicate = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation updated",
                description="Different wording with the same stable identity.",
                created_at=created_at,
                updated_at=created_at,
            )

            storage.save_hypotheses("NVDA", [first])
            storage.save_hypotheses("NVDA", [duplicate])

            loaded = storage.load_hypotheses("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("Momentum continuation", loaded[0].title)


if __name__ == "__main__":
    unittest.main()