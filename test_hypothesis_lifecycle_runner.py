import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL
from research.runner import run_manual_hypothesis_lifecycle


class ManualHypothesisLifecycleRunnerTests(unittest.TestCase):
    def test_runner_output_is_human_readable_and_recommendation_only(self):
        storage = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=24,
                average_return=-0.01,
                win_rate=0.40,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        second_completed_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=10,
                average_return=-0.02,
                win_rate=0.42,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        storage.load_experiment_results.return_value = [
            completed_result,
            second_completed_result,
        ]
        storage.load_hypothesis_reviews.return_value = []

        with patch("builtins.print") as mock_print:
            recommendations = run_manual_hypothesis_lifecycle(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(recommendations))
        mock_print.assert_any_call("Manual Hypothesis Lifecycle: NVDA")
        mock_print.assert_any_call("Recommendations only; no hypothesis state is changed.")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Lifecycle Recommendations : 1")
        mock_print.assert_any_call("Hypothesis Lifecycle Recommendations")
        mock_print.assert_any_call(
            "- Momentum continuation [active] id=hyp-001 action=retire_candidate"
        )

    def test_runner_does_not_mutate_or_persist_hypotheses(self):
        storage = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-immutable",
            symbol="NVDA",
            title="Original claim",
            description="Original claim text must not change.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.55,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []

        result = run_manual_hypothesis_lifecycle(symbol=DEFAULT_SYMBOL, storage=storage)

        self.assertEqual(1, len(result))
        self.assertEqual("Original claim", hypothesis.title)
        self.assertEqual("Original claim text must not change.", hypothesis.description)
        self.assertEqual(HypothesisStatus.ACTIVE, hypothesis.status)
        self.assertEqual(0.55, hypothesis.confidence)
        storage.save_hypotheses.assert_not_called()

    def test_runner_selects_newest_review_for_same_hypothesis(self):
        storage = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=24,
                average_return=-0.01,
                win_rate=0.40,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        second_completed_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=10,
                average_return=-0.02,
                win_rate=0.42,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        storage.load_experiment_results.return_value = [
            completed_result,
            second_completed_result,
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-older",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Older review.",
                confidence=0.65,
                created_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            ),
            HypothesisReview(
                review_id="hyprev-newer",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.RETIRE,
                rationale="Newer review.",
                confidence=0.72,
                created_at=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        with patch("builtins.print") as mock_print:
            recommendations = run_manual_hypothesis_lifecycle(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(recommendations))
        self.assertEqual("hyprev-newer", recommendations[0].review_id)
        self.assertEqual(
            HypothesisReviewRecommendation.RETIRE,
            recommendations[0].review_recommendation,
        )
        mock_print.assert_any_call("  latest_review=retire, confidence=0.72, id=hyprev-newer")

    def test_runner_selects_later_appended_review_when_created_at_is_tied(self):
        storage = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=24,
                average_return=-0.01,
                win_rate=0.40,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        second_completed_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=10,
                average_return=-0.02,
                win_rate=0.42,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        storage.load_experiment_results.return_value = [
            completed_result,
            second_completed_result,
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-earlier-appended",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Earlier appended review.",
                confidence=0.61,
                created_at=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
            ),
            HypothesisReview(
                review_id="hyprev-later-appended",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.RETIRE,
                rationale="Later appended review with same timestamp.",
                confidence=0.79,
                created_at=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        with patch("builtins.print") as mock_print:
            recommendations = run_manual_hypothesis_lifecycle(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(recommendations))
        self.assertEqual("hyprev-later-appended", recommendations[0].review_id)
        self.assertEqual(
            HypothesisReviewRecommendation.RETIRE,
            recommendations[0].review_recommendation,
        )
        mock_print.assert_any_call("  latest_review=retire, confidence=0.79, id=hyprev-later-appended")


if __name__ == "__main__":
    unittest.main()
