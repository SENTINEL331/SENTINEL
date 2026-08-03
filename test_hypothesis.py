import unittest
from datetime import datetime, timezone

from research.hypothesis import Hypothesis, HypothesisStatus


class HypothesisTests(unittest.TestCase):
    def test_construction_exposes_domain_fields_and_aliases(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Price strength may continue after an earnings-driven breakout.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.65,
            source_observation_ids=("obs-1", "obs-2"),
            parent_hypothesis_id="hyp-root",
            lineage_hypothesis_ids=("hyp-root",),
            experiment_refs=("exp-1",),
            created_at=created_at,
            updated_at=created_at,
        )

        self.assertEqual("hyp-001", hypothesis.hypothesis_id)
        self.assertEqual("hyp-001", hypothesis.id)
        self.assertEqual("NVDA", hypothesis.symbol)
        self.assertEqual(HypothesisStatus.ACTIVE, hypothesis.status)
        self.assertEqual(("obs-1", "obs-2"), hypothesis.source_observation_ids)
        self.assertEqual(("obs-1", "obs-2"), hypothesis.observations)
        self.assertEqual(("exp-1",), hypothesis.experiment_refs)
        self.assertEqual(("exp-1",), hypothesis.experiments)
        self.assertEqual("2026-08-03T00:00:00+00:00", hypothesis.created)
        self.assertEqual("2026-08-03T00:00:00+00:00", hypothesis.updated)

    def test_domain_helpers_return_new_instances(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2026, 8, 3, 0, 5, tzinfo=timezone.utc)

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Price strength may continue after an earnings-driven breakout.",
            created_at=created_at,
            updated_at=created_at,
        )

        refined = hypothesis.with_status(HypothesisStatus.SUPPORTED, updated_at)
        refined = refined.with_confidence(0.8, updated_at)
        refined = refined.add_source_observation("obs-3", updated_at)
        refined = refined.add_experiment_reference("exp-2", updated_at)
        refined = refined.with_parent("hyp-root", ancestor_ids=("hyp-anc-1",), updated_at=updated_at)

        self.assertIsNot(hypothesis, refined)
        self.assertEqual(HypothesisStatus.SUPPORTED, refined.status)
        self.assertEqual(0.8, refined.confidence)
        self.assertEqual(("obs-3",), refined.source_observation_ids)
        self.assertEqual(("exp-2",), refined.experiment_refs)
        self.assertEqual("hyp-root", refined.parent_hypothesis_id)
        self.assertEqual(("hyp-anc-1", "hyp-root"), refined.lineage_hypothesis_ids)
        self.assertEqual(updated_at, refined.updated_at)

        self.assertEqual(HypothesisStatus.PROPOSED, hypothesis.status)
        self.assertEqual(0.0, hypothesis.confidence)
        self.assertEqual((), hypothesis.source_observation_ids)
        self.assertEqual((), hypothesis.experiment_refs)

    def test_rejects_invalid_confidence_and_naive_timestamps(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        with self.assertRaises(ValueError):
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                confidence=1.2,
                created_at=created_at,
                updated_at=created_at,
            )

        with self.assertRaises(ValueError):
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                created_at=datetime(2026, 8, 3, 0, 0),
                updated_at=created_at,
            )


if __name__ == "__main__":
    unittest.main()