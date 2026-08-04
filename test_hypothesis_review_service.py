import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.hypothesis_review_service import HypothesisReviewService
from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation


class HypothesisReviewServiceTests(unittest.TestCase):
    def test_generate_for_symbol_calls_ai_parses_and_saves(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()

        ai_client.hypothesis_review.return_value = """
        {
            "hypothesis_reviews": [
                {
                    "review_id": "hyprev-001",
                    "hypothesis_id": "hyp-001",
                    "symbol": "NVDA",
                    "recommendation": "keep",
                    "rationale": "Evidence remains positive and stable.",
                    "confidence": 0.76,
                    "created_at": "2026-08-04T00:00:00+00:00"
                }
            ]
        }
        """

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.68,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []

        service = HypothesisReviewService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        reviews = service.generate_for_symbol(symbol="NVDA")

        self.assertEqual(1, len(reviews))
        self.assertIsInstance(reviews[0], HypothesisReview)
        self.assertEqual("hyprev-001", reviews[0].review_id)
        self.assertEqual(HypothesisReviewRecommendation.KEEP, reviews[0].recommendation)
        self.assertEqual(0.76, reviews[0].confidence)
        self.assertEqual(datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc), reviews[0].created_at)

        storage.load_hypotheses.assert_called_once_with("NVDA")
        storage.load_experiment_requests.assert_called_once_with("NVDA")
        storage.load_experiment_results.assert_called_once_with("NVDA")
        journal_builder.build.assert_not_called()
        ai_client.hypothesis_review.assert_called_once()
        storage.save_hypothesis_reviews.assert_called_once_with("NVDA", reviews)

        call_kwargs = ai_client.hypothesis_review.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertIn("Hypothesis Review Context: NVDA", call_kwargs["journal"])
        self.assertIn("Included Completed Executable Results: 0", call_kwargs["journal"])
        self.assertIn("hyp-001", call_kwargs["hypotheses"])
        self.assertIn("Momentum continuation", call_kwargs["hypotheses"])

    def test_generate_for_symbol_excludes_stale_failures_and_includes_completed_metrics(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()

        ai_client.hypothesis_review.return_value = '{"hypothesis_reviews": []}'

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.68,
        )

        executable_request = ExperimentRequest(
            experiment_request_id="expreq-exec-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Executable request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.PROPOSED,
        )

        obsolete_request = ExperimentRequest(
            experiment_request_id="expreq-obsolete-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Obsolete request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.REJECTED,
        )

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_executable_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-exec-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=24,
                average_return=0.0125,
                win_rate=0.60,
                extra_metrics={
                    "best_return": 0.07,
                    "worst_return": -0.03,
                },
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )

        failed_legacy_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-exec-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.FAILED,
            started_at=now,
            completed_at=now,
            failure_reason="unknown-field-error-from-legacy-run",
            created_at=now,
            updated_at=now,
        )

        not_implemented_legacy_result = ExperimentResult(
            experiment_result_id="expr-003",
            experiment_request_id="expreq-exec-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.NOT_IMPLEMENTED,
            started_at=now,
            completed_at=now,
            failure_reason="unsupported_experiment_request",
            created_at=now,
            updated_at=now,
        )

        completed_obsolete_result = ExperimentResult(
            experiment_result_id="expr-004",
            experiment_request_id="expreq-obsolete-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(trade_count=100, average_return=0.5, win_rate=1.0),
            summary="Should be excluded.",
            created_at=now,
            updated_at=now,
        )

        completed_unknown_request_result = ExperimentResult(
            experiment_result_id="expr-005",
            experiment_request_id="missing-request",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(trade_count=100, average_return=0.5, win_rate=1.0),
            summary="Should be excluded.",
            created_at=now,
            updated_at=now,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = [executable_request, obsolete_request]
        storage.load_experiment_results.return_value = [
            completed_executable_result,
            failed_legacy_result,
            not_implemented_legacy_result,
            completed_obsolete_result,
            completed_unknown_request_result,
        ]

        service = HypothesisReviewService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        service.generate_for_symbol(symbol="NVDA")

        call_kwargs = ai_client.hypothesis_review.call_args.kwargs
        review_context = call_kwargs["journal"]

        self.assertIn("Included Completed Executable Results: 1", review_context)
        self.assertIn("Excluded Non-Completed Results: 2", review_context)
        self.assertIn("Excluded Non-Executable/Legacy Results: 2", review_context)
        self.assertIn("average_return=1.25%", review_context)
        self.assertIn("win_rate=60.00%", review_context)
        self.assertIn("best_return=7.00%", review_context)
        self.assertIn("worst_return=-3.00%", review_context)
        self.assertIn("Evidence is currently insufficient", review_context)
        self.assertNotIn("unknown-field-error-from-legacy-run", review_context)
        self.assertNotIn("unsupported_experiment_request", review_context)

    def test_generate_for_symbol_rejects_invalid_hypothesis_inputs(self):
        service = HypothesisReviewService(
            ai_client=Mock(),
            storage=Mock(),
            journal_builder=Mock(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "hypotheses must be a JSON string, dicts, or Hypothesis objects",
        ):
            service.generate_for_symbol(
                symbol="NVDA",
                journal="Journal context.",
                hypotheses=[123],
            )


if __name__ == "__main__":
    unittest.main()
