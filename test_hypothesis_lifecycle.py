import unittest
from datetime import datetime, timezone

from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_evaluation import HypothesisEvidenceSummary
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions


def _completed_result(
    *,
    result_id: str,
    hypothesis_id: str,
    trade_count: int | None = None,
    average_return: float | None = None,
    win_rate: float | None = None,
) -> ExperimentResult:
    now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

    return ExperimentResult(
        experiment_result_id=result_id,
        experiment_request_id=f"req-{result_id}",
        hypothesis_id=hypothesis_id,
        symbol="NVDA",
        test_type=ExperimentTestType.INITIAL_BACKTEST,
        status=ExperimentResultStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        metrics=ExperimentMetrics(
            trade_count=trade_count,
            average_return=average_return,
            win_rate=win_rate,
        ),
        summary="completed",
        created_at=now,
        updated_at=now,
    )


class HypothesisLifecyclePolicyTests(unittest.TestCase):
    def test_untested_hypothesis_recommends_needs_more_tests(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-untested",
            symbol="NVDA",
            title="Untested hypothesis",
            description="No completed experiments.",
            status=HypothesisStatus.ACTIVE,
        )

        evidence = evaluate_hypothesis_evidence([hypothesis], [])
        recommendations = recommend_hypothesis_lifecycle_actions([hypothesis], evidence)

        self.assertEqual(1, len(recommendations))
        self.assertEqual(
            HypothesisLifecycleAction.NEEDS_MORE_TESTS,
            recommendations[0].action,
        )

    def test_repeated_zero_trade_evidence_recommends_refine_candidate(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-zero-trade",
            symbol="NVDA",
            title="Zero trade setup",
            description="Entry conditions are too restrictive.",
            status=HypothesisStatus.ACTIVE,
        )
        results = [
            _completed_result(
                result_id="expr-001",
                hypothesis_id="hyp-zero-trade",
                trade_count=0,
            ),
            _completed_result(
                result_id="expr-002",
                hypothesis_id="hyp-zero-trade",
                trade_count=0,
            ),
        ]

        evidence = evaluate_hypothesis_evidence([hypothesis], results)
        self.assertEqual(HypothesisEvidenceStatus.INSUFFICIENT_DATA, evidence[0].evidence_status)
        self.assertEqual(2, evidence[0].zero_trade_completed_experiment_count)

        recommendations = recommend_hypothesis_lifecycle_actions([hypothesis], evidence)

        self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, recommendations[0].action)

    def test_weak_evidence_below_minimum_sample_does_not_recommend_retire_candidate(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-low-sample",
            symbol="NVDA",
            title="Low sample weak hypothesis",
            description="Weak-looking but underpowered evidence.",
            status=HypothesisStatus.ACTIVE,
        )
        evidence = [
            HypothesisEvidenceSummary(
                hypothesis_id="hyp-low-sample",
                hypothesis_title="Low sample weak hypothesis",
                completed_experiment_count=2,
                zero_trade_completed_experiment_count=0,
                total_trade_count=10,
                average_return=-0.01,
                win_rate=0.4,
                best_return=0.01,
                worst_return=-0.03,
                evidence_status=HypothesisEvidenceStatus.WEAK,
            )
        ]

        recommendations = recommend_hypothesis_lifecycle_actions([hypothesis], evidence)

        self.assertNotEqual(HypothesisLifecycleAction.RETIRE_CANDIDATE, recommendations[0].action)

    def test_weak_evidence_above_minimum_sample_can_recommend_retire_candidate(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-weak-mature",
            symbol="NVDA",
            title="Mature weak hypothesis",
            description="Persistently weak evidence with sufficient sample.",
            status=HypothesisStatus.ACTIVE,
        )
        results = [
            _completed_result(
                result_id="expr-101",
                hypothesis_id="hyp-weak-mature",
                trade_count=15,
                average_return=-0.01,
                win_rate=0.4,
            ),
            _completed_result(
                result_id="expr-102",
                hypothesis_id="hyp-weak-mature",
                trade_count=12,
                average_return=-0.02,
                win_rate=0.42,
            ),
        ]

        evidence = evaluate_hypothesis_evidence([hypothesis], results)
        self.assertEqual(HypothesisEvidenceStatus.WEAK, evidence[0].evidence_status)

        recommendations = recommend_hypothesis_lifecycle_actions([hypothesis], evidence)

        self.assertEqual(HypothesisLifecycleAction.RETIRE_CANDIDATE, recommendations[0].action)

    def test_policy_does_not_mutate_hypothesis_objects(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-immutable",
            symbol="NVDA",
            title="Immutable claim",
            description="Original claim must remain unchanged.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.6,
        )
        original = hypothesis

        evidence = evaluate_hypothesis_evidence([hypothesis], [])
        _ = recommend_hypothesis_lifecycle_actions([hypothesis], evidence)

        self.assertIs(hypothesis, original)
        self.assertEqual("Immutable claim", hypothesis.title)
        self.assertEqual("Original claim must remain unchanged.", hypothesis.description)
        self.assertEqual(HypothesisStatus.ACTIVE, hypothesis.status)
        self.assertEqual(0.6, hypothesis.confidence)


if __name__ == "__main__":
    unittest.main()
