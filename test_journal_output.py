import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.journal import ResearchJournal
from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.experiment_result import (
    ExperimentMetrics,
    ExperimentResult,
    ExperimentResultStatus,
)
from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.observation import Observation


class ResearchJournalOutputTests(unittest.TestCase):
    def test_build_includes_experiment_requests_section(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = [
            Observation(
                observation_id="obs-1",
                symbol_id="NVDA",
                statement="Price closed above the configured breakout range.",
                evidence_refs=["snapshot:NVDA:2026-08-03"],
                importance=1,
                effective_time="2026-08-03",
                created_at="2026-08-03T00:00:00+00:00",
                research_cycle_id="cycle-001",
                ai_call_id="ai-001",
            )
        ]
        journal.storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.75,
                source_observation_ids=("obs-1",),
            )
        ]
        journal.storage.load_experiment_requests.return_value = [
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Test whether breakout continuation persists over five sessions.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Enter after breakout close above prior 20-day high.",
                exit_conditions="Exit on stop breach or five-session horizon.",
                time_horizon="5D",
                status=ExperimentRequestStatus.PROPOSED,
                source_observation_ids=("obs-1",),
            )
        ]
        journal.storage.load_experiment_results.return_value = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 3, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    total_return=0.12,
                    win_rate=0.60,
                    max_drawdown=-0.08,
                    trade_count=25,
                    profit_factor=1.4,
                ),
                summary="Completed with positive expectancy and manageable drawdown.",
            )
        ]
        journal.storage.load_hypothesis_reviews.return_value = []
        journal.storage.load_hypothesis_revision_proposals.return_value = []
        journal.storage.load_hypothesis_revision_applications.return_value = []

        result = journal.build("NVDA")

        self.assertIn("Observations", result)
        self.assertIn("Price closed above the configured breakout range.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn(
            "- Momentum continuation [active] confidence=0.75 id=hyp-001",
            result,
        )
        self.assertIn("Experiment Requests", result)
        self.assertIn(
            "- Validate momentum continuation [proposed] test_type=initial_backtest id=expreq-001",
            result,
        )
        self.assertIn(
            "  objective: Test whether breakout continuation persists over five sessions.",
            result,
        )
        self.assertIn("Experiment Results", result)
        self.assertIn(
            "- initial_backtest [completed] id=expr-001",
            result,
        )
        self.assertIn(
            "  metrics: total_return=0.1200, win_rate=0.6000, max_drawdown=-0.0800, trade_count=25, profit_factor=1.4000",
            result,
        )
        self.assertIn(
            "  detail: Completed with positive expectancy and manageable drawdown.",
            result,
        )
        self.assertIn("Hypothesis Evidence", result)
        self.assertIn(
            "- Momentum continuation [insufficient_data] id=hyp-001",
            result,
        )
        self.assertIn(
            "  completed_experiments=1, trade_count=25, average_return=n/a, win_rate=60.00%, best_return=n/a, worst_return=n/a",
            result,
        )
        self.assertIn("Latest Hypothesis Reviews", result)
        self.assertIn("No hypothesis reviews.", result)
        self.assertIn("Hypothesis Lifecycle Recommendations", result)
        self.assertIn("Recommendations only; no hypothesis state is changed.", result)
        self.assertIn(
            "- Momentum continuation [active] id=hyp-001 action=needs_more_tests",
            result,
        )
        self.assertIn(
            "  evidence=insufficient_data, completed_experiments=1, trade_count=25",
            result,
        )
        self.assertIn("Hypothesis Revision Proposals", result)
        self.assertIn("Proposals are records only and are never auto-applied.", result)
        self.assertIn("No hypothesis revision proposals.", result)
        self.assertIn("Hypothesis Lineage", result)
        self.assertIn("No hypothesis lineage records.", result)

    def test_build_shows_empty_experiment_requests_state(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = []
        journal.storage.load_hypotheses.return_value = []
        journal.storage.load_experiment_requests.return_value = []
        journal.storage.load_experiment_results.return_value = []
        journal.storage.load_hypothesis_reviews.return_value = []
        journal.storage.load_hypothesis_revision_proposals.return_value = []
        journal.storage.load_hypothesis_revision_applications.return_value = []

        result = journal.build("NVDA")

        self.assertIn("Observations", result)
        self.assertIn("No previous observations.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn("No active hypotheses.", result)
        self.assertIn("Experiment Requests", result)
        self.assertIn("No experiment requests.", result)
        self.assertIn("Experiment Results", result)
        self.assertIn("No experiment results.", result)
        self.assertIn("Hypothesis Evidence", result)
        self.assertIn("No hypothesis evidence.", result)
        self.assertIn("Latest Hypothesis Reviews", result)
        self.assertIn("No hypothesis reviews.", result)
        self.assertIn("Hypothesis Lifecycle Recommendations", result)
        self.assertIn("Recommendations only; no hypothesis state is changed.", result)
        self.assertIn("No lifecycle recommendations.", result)
        self.assertIn("Hypothesis Revision Proposals", result)
        self.assertIn("No hypothesis revision proposals.", result)
        self.assertIn("Hypothesis Lineage", result)
        self.assertIn("No hypothesis lineage records.", result)

    def test_build_formats_hypothesis_evidence_percentages_when_available(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = []
        journal.storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-002",
                symbol="NVDA",
                title="Trend continuation",
                description="Trend may persist for several sessions.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.65,
            )
        ]
        journal.storage.load_experiment_requests.return_value = []
        journal.storage.load_experiment_results.return_value = [
            ExperimentResult(
                experiment_result_id="expr-101",
                experiment_request_id="expreq-101",
                hypothesis_id="hyp-002",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 3, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=15,
                    average_return=0.01,
                    win_rate=0.60,
                    extra_metrics={
                        "best_return": 0.05,
                        "worst_return": -0.02,
                    },
                ),
                summary="Completed result one.",
            ),
            ExperimentResult(
                experiment_result_id="expr-102",
                experiment_request_id="expreq-102",
                hypothesis_id="hyp-002",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 4, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=10,
                    average_return=0.02,
                    win_rate=0.70,
                    extra_metrics={
                        "best_return": 0.08,
                        "worst_return": -0.03,
                    },
                ),
                summary="Completed result two.",
            ),
        ]
        journal.storage.load_hypothesis_reviews.return_value = []
        journal.storage.load_hypothesis_revision_proposals.return_value = []
        journal.storage.load_hypothesis_revision_applications.return_value = []

        result = journal.build("NVDA")

        self.assertIn(
            "- Trend continuation [promising] id=hyp-002",
            result,
        )
        self.assertIn(
            "  completed_experiments=2, trade_count=25, average_return=1.50%, win_rate=65.00%, best_return=8.00%, worst_return=-3.00%",
            result,
        )

    def test_build_includes_latest_hypothesis_review_per_hypothesis(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = []
        journal.storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after a breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.7,
            ),
            Hypothesis(
                hypothesis_id="hyp-002",
                symbol="NVDA",
                title="Mean reversion",
                description="Short-term spikes may revert quickly.",
                status=HypothesisStatus.PROPOSED,
                confidence=0.55,
            ),
        ]
        journal.storage.load_experiment_requests.return_value = []
        journal.storage.load_experiment_results.return_value = []
        journal.storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Completed evidence supports keeping current framing.",
                confidence=0.62,
                created_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
            ),
            HypothesisReview(
                review_id="hyprev-002",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Refine entry criteria to reduce noisy triggers.",
                confidence=0.71,
                created_at=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
            ),
            HypothesisReview(
                review_id="hyprev-003",
                hypothesis_id="hyp-002",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Insufficient coverage across volatility regimes.",
                confidence=0.58,
                created_at=datetime(2026, 8, 2, 8, 30, tzinfo=timezone.utc),
            ),
        ]
        journal.storage.load_hypothesis_revision_proposals.return_value = []
        journal.storage.load_hypothesis_revision_applications.return_value = []

        result = journal.build("NVDA")

        self.assertIn("Latest Hypothesis Reviews", result)
        self.assertIn("- Momentum continuation id=hyp-001", result)
        self.assertIn(
            "  recommendation=refine, confidence=0.71, created_at=2026-08-04T12:00:00+00:00",
            result,
        )
        self.assertIn(
            "  rationale: Refine entry criteria to reduce noisy triggers.",
            result,
        )
        self.assertNotIn(
            "recommendation=keep, confidence=0.62, created_at=2026-08-03T12:00:00+00:00",
            result,
        )
        self.assertIn("- Mean reversion id=hyp-002", result)
        self.assertIn(
            "  recommendation=needs_more_tests, confidence=0.58, created_at=2026-08-02T08:30:00+00:00",
            result,
        )
        self.assertIn("Hypothesis Lifecycle Recommendations", result)
        self.assertIn(
            "- Momentum continuation [active] id=hyp-001 action=needs_more_tests",
            result,
        )
        self.assertIn(
            "  latest_review=refine",
            result,
        )

    def test_build_includes_revision_proposal_and_lineage_sections(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)

        journal.storage.load_observations.return_value = []
        journal.storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent hypothesis",
                description="Parent description.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.7,
            ),
            Hypothesis(
                hypothesis_id="hyp-002",
                symbol="NVDA",
                title="Child hypothesis",
                description="Child description.",
                status=HypothesisStatus.PROPOSED,
                confidence=0.65,
                parent_hypothesis_id="hyp-001",
                lineage_hypothesis_ids=("hyp-001",),
                source_revision_proposal_id="hyprevp-001",
            ),
        ]
        journal.storage.load_experiment_requests.return_value = []
        journal.storage.load_experiment_results.return_value = []
        journal.storage.load_hypothesis_reviews.return_value = []
        journal.storage.load_hypothesis_revision_proposals.return_value = [
            HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id="hyprev-001",
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Child hypothesis",
                proposed_description="Child description.",
                rationale="Refine to a narrower setup.",
                confidence=0.68,
                created_at=now,
            )
        ]
        journal.storage.load_hypothesis_revision_applications.return_value = [
            HypothesisRevisionApplication(
                application_id="hypreva-001",
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                status=HypothesisRevisionApplicationStatus.APPLIED,
                apply_mode=True,
                child_hypothesis_id="hyp-002",
                message="proposal applied",
                created_at=now,
            )
        ]

        result = journal.build("NVDA")

        self.assertIn("Hypothesis Revision Proposals", result)
        self.assertIn(
            "- parent_id=hyp-001 proposal_type=create_child_hypothesis lifecycle_action=refine_candidate confidence=0.68 id=hyprevp-001",
            result,
        )
        self.assertIn("  applied_status=applied", result)
        self.assertIn("  child_hypothesis_id=hyp-002", result)
        self.assertIn("Hypothesis Lineage", result)
        self.assertIn(
            "- Child hypothesis id=hyp-002 parent_id=hyp-001 source_revision_proposal_id=hyprevp-001 lineage=hyp-001",
            result,
        )


if __name__ == "__main__":
    unittest.main()