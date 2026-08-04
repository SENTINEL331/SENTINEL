import unittest
from datetime import datetime, timezone

from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence


def _result(
    *,
    result_id: str,
    request_id: str,
    hypothesis_id: str,
    status: ExperimentResultStatus,
    trade_count: int | None = None,
    average_return: float | None = None,
    win_rate: float | None = None,
    best_return: float | None = None,
    worst_return: float | None = None,
) -> ExperimentResult:
    now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
    extra_metrics = {}
    if best_return is not None:
        extra_metrics["best_return"] = best_return

    if worst_return is not None:
        extra_metrics["worst_return"] = worst_return

    return ExperimentResult(
        experiment_result_id=result_id,
        experiment_request_id=request_id,
        hypothesis_id=hypothesis_id,
        symbol="NVDA",
        test_type=ExperimentTestType.INITIAL_BACKTEST,
        status=status,
        started_at=now,
        completed_at=now if status != ExperimentResultStatus.RUNNING else None,
        metrics=ExperimentMetrics(
            trade_count=trade_count,
            average_return=average_return,
            win_rate=win_rate,
            extra_metrics=extra_metrics,
        ),
        summary="summary",
        failure_reason=("failure" if status != ExperimentResultStatus.COMPLETED else None),
        created_at=now,
        updated_at=now,
    )


class HypothesisEvaluationTests(unittest.TestCase):
    def test_evaluate_hypothesis_evidence_assigns_expected_statuses(self):
        hypotheses = [
            Hypothesis(
                hypothesis_id="hyp-untested",
                symbol="NVDA",
                title="Untested",
                description="No completed experiments.",
                status=HypothesisStatus.ACTIVE,
            ),
            Hypothesis(
                hypothesis_id="hyp-insufficient",
                symbol="NVDA",
                title="Insufficient",
                description="Too little data.",
                status=HypothesisStatus.ACTIVE,
            ),
            Hypothesis(
                hypothesis_id="hyp-promising",
                symbol="NVDA",
                title="Promising",
                description="Positive and high win rate.",
                status=HypothesisStatus.ACTIVE,
            ),
            Hypothesis(
                hypothesis_id="hyp-weak",
                symbol="NVDA",
                title="Weak",
                description="Negative and low win rate.",
                status=HypothesisStatus.ACTIVE,
            ),
            Hypothesis(
                hypothesis_id="hyp-mixed",
                symbol="NVDA",
                title="Mixed",
                description="Conflicting evidence.",
                status=HypothesisStatus.ACTIVE,
            ),
        ]

        results = [
            _result(
                result_id="expr-insufficient-1",
                request_id="req-insufficient-1",
                hypothesis_id="hyp-insufficient",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=5,
                average_return=0.01,
                win_rate=0.60,
                best_return=0.03,
                worst_return=-0.01,
            ),
            _result(
                result_id="expr-promising-1",
                request_id="req-promising-1",
                hypothesis_id="hyp-promising",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=20,
                average_return=0.02,
                win_rate=0.60,
                best_return=0.08,
                worst_return=-0.02,
            ),
            _result(
                result_id="expr-promising-2",
                request_id="req-promising-2",
                hypothesis_id="hyp-promising",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=20,
                average_return=0.01,
                win_rate=0.70,
                best_return=0.06,
                worst_return=-0.03,
            ),
            _result(
                result_id="expr-weak-1",
                request_id="req-weak-1",
                hypothesis_id="hyp-weak",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=15,
                average_return=-0.01,
                win_rate=0.40,
                best_return=0.02,
                worst_return=-0.06,
            ),
            _result(
                result_id="expr-weak-2",
                request_id="req-weak-2",
                hypothesis_id="hyp-weak",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=20,
                average_return=-0.02,
                win_rate=0.45,
                best_return=0.01,
                worst_return=-0.08,
            ),
            _result(
                result_id="expr-mixed-1",
                request_id="req-mixed-1",
                hypothesis_id="hyp-mixed",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=12,
                average_return=0.01,
                win_rate=0.51,
                best_return=0.04,
                worst_return=-0.05,
            ),
            _result(
                result_id="expr-mixed-2",
                request_id="req-mixed-2",
                hypothesis_id="hyp-mixed",
                status=ExperimentResultStatus.COMPLETED,
                trade_count=12,
                average_return=0.00,
                win_rate=0.49,
                best_return=0.03,
                worst_return=-0.04,
            ),
            _result(
                result_id="expr-ignore-failed",
                request_id="req-ignore-failed",
                hypothesis_id="hyp-promising",
                status=ExperimentResultStatus.FAILED,
            ),
        ]

        summaries = evaluate_hypothesis_evidence(hypotheses, results)

        by_id = {summary.hypothesis_id: summary for summary in summaries}
        self.assertEqual(HypothesisEvidenceStatus.UNTESTED, by_id["hyp-untested"].evidence_status)
        self.assertEqual(
            HypothesisEvidenceStatus.INSUFFICIENT_DATA,
            by_id["hyp-insufficient"].evidence_status,
        )
        self.assertEqual(HypothesisEvidenceStatus.PROMISING, by_id["hyp-promising"].evidence_status)
        self.assertEqual(HypothesisEvidenceStatus.WEAK, by_id["hyp-weak"].evidence_status)
        self.assertEqual(HypothesisEvidenceStatus.MIXED, by_id["hyp-mixed"].evidence_status)

        self.assertEqual(2, by_id["hyp-promising"].completed_experiment_count)
        self.assertEqual(40, by_id["hyp-promising"].total_trade_count)
        self.assertAlmostEqual(0.015, by_id["hyp-promising"].average_return)
        self.assertAlmostEqual(0.65, by_id["hyp-promising"].win_rate)
        self.assertEqual(0.08, by_id["hyp-promising"].best_return)
        self.assertEqual(-0.03, by_id["hyp-promising"].worst_return)


if __name__ == "__main__":
    unittest.main()