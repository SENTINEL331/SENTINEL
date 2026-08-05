import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

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
from research.research_plan import ResearchPlan
from research.research_plan import ResearchPlanAction
from research.research_plan import ResearchPlanItem
from research.research_plan import ResearchPlanPriority
from research.runner import run_manual_research_dashboard


class ManualResearchDashboardRunnerTests(unittest.TestCase):
    def _build_storage(self, data_by_symbol):
        storage = Mock()
        storage.load_hypotheses.side_effect = lambda symbol: data_by_symbol[symbol]["hypotheses"]
        storage.load_experiment_requests.side_effect = lambda symbol: data_by_symbol[symbol][
            "experiment_requests"
        ]
        storage.load_experiment_results.side_effect = lambda symbol: data_by_symbol[symbol][
            "experiment_results"
        ]
        storage.load_hypothesis_reviews.side_effect = lambda symbol: data_by_symbol[symbol][
            "hypothesis_reviews"
        ]
        storage.load_hypothesis_revision_proposals.side_effect = lambda symbol: data_by_symbol[symbol][
            "revision_proposals"
        ]
        storage.load_hypothesis_revision_applications.side_effect = lambda symbol: data_by_symbol[symbol][
            "revision_applications"
        ]
        return storage

    def test_dashboard_defaults_to_watchlist_and_is_read_only(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA parent",
                        description="Parent hypothesis.",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    ),
                    Hypothesis(
                        hypothesis_id="hyp-nvda-child-001",
                        symbol="NVDA",
                        title="NVDA child",
                        description="Child hypothesis.",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        parent_hypothesis_id="hyp-nvda-001",
                        created_at=now,
                        updated_at=now,
                    ),
                ],
                "experiment_requests": [
                    ExperimentRequest(
                        experiment_request_id="expreq-nvda-001",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_version_id="hyp-nvda-001:v1",
                        symbol="NVDA",
                        title="Executable",
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
                ],
                "experiment_results": [
                    ExperimentResult(
                        experiment_result_id="expr-nvda-001",
                        experiment_request_id="expreq-nvda-001",
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        test_type=ExperimentTestType.INITIAL_BACKTEST,
                        status=ExperimentResultStatus.COMPLETED,
                        started_at=now,
                        completed_at=now,
                        metrics=ExperimentMetrics(trade_count=8, average_return=0.01, win_rate=0.6),
                        summary="Completed",
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "hypothesis_reviews": [
                    HypothesisReview(
                        review_id="hyprev-nvda-001",
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        recommendation=HypothesisReviewRecommendation.KEEP,
                        rationale="Keep.",
                        confidence=0.6,
                        created_at=now,
                    )
                ],
                "revision_proposals": [],
                "revision_applications": [],
            },
            "AAPL": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-aapl-001",
                        symbol="AAPL",
                        title="AAPL parent",
                        description="Parent hypothesis.",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            },
        }
        storage = self._build_storage(data_by_symbol)

        def _plan_for_symbol(*, symbol, **kwargs):
            if symbol == "NVDA":
                return ResearchPlan(
                    symbol="NVDA",
                    items=(
                        ResearchPlanItem(
                            symbol="NVDA",
                            hypothesis_id="hyp-nvda-001",
                            hypothesis_title="NVDA parent",
                            recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                            priority=ResearchPlanPriority.HIGH,
                            reason="Needs initial request.",
                        ),
                        ResearchPlanItem(
                            symbol="NVDA",
                            hypothesis_id="hyp-nvda-child-001",
                            hypothesis_title="NVDA child",
                            recommended_action=ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW,
                            priority=ResearchPlanPriority.MEDIUM,
                            reason="Needs review.",
                        ),
                    ),
                )

            return ResearchPlan(
                symbol="AAPL",
                items=(
                    ResearchPlanItem(
                        symbol="AAPL",
                        hypothesis_id="hyp-aapl-001",
                        hypothesis_title="AAPL parent",
                        recommended_action=ResearchPlanAction.NO_ACTION,
                        priority=ResearchPlanPriority.LOW,
                        reason="No action.",
                    ),
                ),
            )

        with patch("research.runner.settings.WATCHLIST", ["NVDA", "AAPL"]), patch(
            "research.runner.build_research_plan",
            side_effect=_plan_for_symbol,
        ), patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentRequestService"
        ) as mock_experiment_request_service, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "research.runner.HypothesisRevisionApplicationService"
        ) as mock_hypothesis_revision_application_service, patch(
            "research.runner.ExperimentExecutor"
        ) as mock_experiment_executor:
            summaries = run_manual_research_dashboard(storage=storage)

        self.assertEqual(["NVDA", "AAPL"], [summary["symbol"] for summary in summaries])
        self.assertEqual(2, len(summaries))

        mock_print.assert_any_call("Manual Research Dashboard")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Symbols Reviewed : 2")
        mock_print.assert_any_call("Per-Symbol Summary")
        mock_print.assert_any_call("Watchlist Action Summary")
        mock_print.assert_any_call("Attention Queue")
        mock_print.assert_any_call("Suggested Next Commands")
        mock_print.assert_any_call("Research dashboard read complete. No records were modified.")

        mock_print.assert_any_call("- NVDA")
        mock_print.assert_any_call(
            "  hypotheses=2, children=1, executable_requests=1, pending_executable_requests=0, completed_results=1"
        )
        mock_print.assert_any_call("  reviews=1, revision_proposals=0, plan_items=2")
        mock_print.assert_any_call("  highest_priority=high")
        mock_print.assert_any_call("  top_action=generate_experiment_request")

        mock_print.assert_any_call("- generate_experiment_request : 1")
        mock_print.assert_any_call("- generate_hypothesis_review : 1")
        mock_print.assert_any_call("- no_action : 1")

        mock_print.assert_any_call(
            "- python -m research.runner research-cycle NVDA --planned-experiments"
        )
        mock_print.assert_any_call("- python -m research.runner research-cycle NVDA --reviews")

        self.assertNotIn(
            call("- python -m research.runner research-cycle NVDA --run-experiments"),
            mock_print.mock_calls,
        )

        self.assertNotIn(
            call("- python -m research.runner research-cycle NVDA --full-safe"),
            mock_print.mock_calls,
        )

        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        mock_hypothesis_revision_application_service.assert_not_called()
        mock_experiment_executor.assert_not_called()

        storage.save_hypotheses.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

    def test_dashboard_explicit_symbols_override_watchlist(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "MSFT": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-msft-001",
                        symbol="MSFT",
                        title="MSFT parent",
                        description="Parent hypothesis.",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            }
        }
        storage = self._build_storage(data_by_symbol)

        with patch("research.runner.settings.WATCHLIST", ["NVDA", "AAPL"]), patch(
            "builtins.print"
        ) as mock_print:
            summaries = run_manual_research_dashboard(symbols=["MSFT"], storage=storage)

        self.assertEqual(1, len(summaries))
        self.assertEqual("MSFT", summaries[0]["symbol"])
        mock_print.assert_any_call("Symbols Reviewed : 1")

    def test_attention_queue_is_priority_ordered_with_stable_symbol_and_id_sorting(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "AAPL": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-aapl-001",
                        symbol="AAPL",
                        title="AAPL",
                        description="AAPL",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            },
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA",
                        description="NVDA",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            },
        }
        storage = self._build_storage(data_by_symbol)

        def _plan_for_symbol(*, symbol, **kwargs):
            if symbol == "AAPL":
                return ResearchPlan(
                    symbol="AAPL",
                    items=(
                        ResearchPlanItem(
                            symbol="AAPL",
                            hypothesis_id="hyp-aapl-002",
                            hypothesis_title="AAPL high",
                            recommended_action=ResearchPlanAction.GENERATE_REVISION_PROPOSAL,
                            priority=ResearchPlanPriority.HIGH,
                            reason="AAPL high",
                        ),
                        ResearchPlanItem(
                            symbol="AAPL",
                            hypothesis_id="hyp-aapl-003",
                            hypothesis_title="AAPL low",
                            recommended_action=ResearchPlanAction.NO_ACTION,
                            priority=ResearchPlanPriority.LOW,
                            reason="AAPL low",
                        ),
                    ),
                )

            return ResearchPlan(
                symbol="NVDA",
                items=(
                    ResearchPlanItem(
                        symbol="NVDA",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_title="NVDA medium",
                        recommended_action=ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW,
                        priority=ResearchPlanPriority.MEDIUM,
                        reason="NVDA medium",
                    ),
                    ResearchPlanItem(
                        symbol="NVDA",
                        hypothesis_id="hyp-nvda-002",
                        hypothesis_title="NVDA high",
                        recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                        priority=ResearchPlanPriority.HIGH,
                        reason="NVDA high",
                    ),
                ),
            )

        with patch("research.runner.build_research_plan", side_effect=_plan_for_symbol), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_research_dashboard(symbols=["AAPL", "NVDA"], storage=storage)

        mock_print.assert_has_calls(
            [
                call(
                    "- symbol=AAPL hypothesis_id=hyp-aapl-002 action=generate_revision_proposal priority=high"
                ),
                call("  reason: AAPL high"),
                call(
                    "- symbol=NVDA hypothesis_id=hyp-nvda-002 action=generate_experiment_request priority=high"
                ),
                call("  reason: NVDA high"),
                call(
                    "- symbol=NVDA hypothesis_id=hyp-nvda-001 action=generate_hypothesis_review priority=medium"
                ),
                call("  reason: NVDA medium"),
                call("- symbol=AAPL hypothesis_id=hyp-aapl-003 action=no_action priority=low"),
                call("  reason: AAPL low"),
            ],
            any_order=False,
        )

    def test_suggested_revision_apply_command_includes_explicit_human_choice_note(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA",
                        description="NVDA",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            }
        }
        storage = self._build_storage(data_by_symbol)

        plan = ResearchPlan(
            symbol="NVDA",
            items=(
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-nvda-001",
                    hypothesis_title="NVDA",
                    recommended_action=ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE,
                    priority=ResearchPlanPriority.MEDIUM,
                    reason="Proposal exists and awaits manual application.",
                ),
            ),
        )

        with patch("research.runner.build_research_plan", return_value=plan), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_research_dashboard(symbols=["NVDA"], storage=storage)

        mock_print.assert_any_call(
            "- python -m research.runner hypothesis-revision-apply NVDA <proposal_id> --dry-run"
        )
        mock_print.assert_any_call(
            "- Note: hypothesis-revision-apply requires a concrete proposal_id and explicit human choice."
        )

    def test_attention_queue_empty_state_is_stable(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA",
                        description="NVDA",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            }
        }
        storage = self._build_storage(data_by_symbol)

        empty_plan = ResearchPlan(symbol="NVDA", items=())

        with patch("research.runner.build_research_plan", return_value=empty_plan), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_research_dashboard(symbols=["NVDA"], storage=storage)

        mock_print.assert_any_call("No attention items found across reviewed symbols.")

    def test_dashboard_suggests_run_experiments_only_for_pending_executable_requests(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA",
                        description="NVDA",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [
                    ExperimentRequest(
                        experiment_request_id="expreq-pending-001",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_version_id="hyp-nvda-001:v1",
                        symbol="NVDA",
                        title="Pending executable",
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
                ],
                "experiment_results": [],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            }
        }
        storage = self._build_storage(data_by_symbol)

        def _plan_for_symbol(*, symbol, **kwargs):
            return ResearchPlan(
                symbol=symbol,
                items=(
                    ResearchPlanItem(
                        symbol=symbol,
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_title="NVDA",
                        recommended_action=ResearchPlanAction.NO_ACTION,
                        priority=ResearchPlanPriority.LOW,
                        reason="No action.",
                    ),
                ),
            )

        with patch("research.runner.settings.WATCHLIST", ["NVDA"]), patch(
            "research.runner.build_research_plan",
            side_effect=_plan_for_symbol,
        ), patch("builtins.print") as mock_print:
            run_manual_research_dashboard(storage=storage)

        mock_print.assert_any_call(
            "- python -m research.runner research-cycle NVDA --run-experiments"
        )

    def test_dashboard_does_not_treat_failed_or_not_implemented_as_completed(self):
        now = datetime.now(timezone.utc)
        data_by_symbol = {
            "NVDA": {
                "hypotheses": [
                    Hypothesis(
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        title="NVDA",
                        description="NVDA",
                        status=HypothesisStatus.ACTIVE,
                        confidence=0.5,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                "experiment_requests": [
                    ExperimentRequest(
                        experiment_request_id="expreq-completed-001",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_version_id="hyp-nvda-001:v1",
                        symbol="NVDA",
                        title="Completed executable",
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
                    ),
                    ExperimentRequest(
                        experiment_request_id="expreq-failed-001",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_version_id="hyp-nvda-001:v1",
                        symbol="NVDA",
                        title="Failed result executable",
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
                    ),
                    ExperimentRequest(
                        experiment_request_id="expreq-legacy-001",
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_version_id="hyp-nvda-001:v1",
                        symbol="NVDA",
                        title="Legacy non-executable",
                        objective="Objective",
                        test_type=ExperimentTestType.INITIAL_BACKTEST,
                        entry_conditions="Entry",
                        exit_conditions="Exit",
                        time_horizon="5D",
                        status=ExperimentRequestStatus.PROPOSED,
                    ),
                ],
                "experiment_results": [
                    ExperimentResult(
                        experiment_result_id="expr-completed-001",
                        experiment_request_id="expreq-completed-001",
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        test_type=ExperimentTestType.INITIAL_BACKTEST,
                        status=ExperimentResultStatus.COMPLETED,
                        started_at=now,
                        completed_at=now,
                        metrics=ExperimentMetrics(trade_count=1, average_return=0.01, win_rate=0.6),
                        summary="Completed",
                        created_at=now,
                        updated_at=now,
                    ),
                    ExperimentResult(
                        experiment_result_id="expr-failed-001",
                        experiment_request_id="expreq-failed-001",
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        test_type=ExperimentTestType.INITIAL_BACKTEST,
                        status=ExperimentResultStatus.FAILED,
                        started_at=now,
                        completed_at=now,
                        metrics=ExperimentMetrics(),
                        summary="Failed",
                        failure_reason="Failed",
                        created_at=now,
                        updated_at=now,
                    ),
                    ExperimentResult(
                        experiment_result_id="expr-notimpl-001",
                        experiment_request_id="expreq-failed-001",
                        hypothesis_id="hyp-nvda-001",
                        symbol="NVDA",
                        test_type=ExperimentTestType.INITIAL_BACKTEST,
                        status=ExperimentResultStatus.NOT_IMPLEMENTED,
                        started_at=now,
                        completed_at=now,
                        metrics=ExperimentMetrics(),
                        summary="Not implemented",
                        failure_reason="Not implemented",
                        created_at=now,
                        updated_at=now,
                    ),
                ],
                "hypothesis_reviews": [],
                "revision_proposals": [],
                "revision_applications": [],
            }
        }
        storage = self._build_storage(data_by_symbol)

        def _plan_for_symbol(*, symbol, **kwargs):
            return ResearchPlan(
                symbol=symbol,
                items=(
                    ResearchPlanItem(
                        symbol=symbol,
                        hypothesis_id="hyp-nvda-001",
                        hypothesis_title="NVDA",
                        recommended_action=ResearchPlanAction.NO_ACTION,
                        priority=ResearchPlanPriority.LOW,
                        reason="No action.",
                    ),
                ),
            )

        with patch("research.runner.settings.WATCHLIST", ["NVDA"]), patch(
            "research.runner.build_research_plan",
            side_effect=_plan_for_symbol,
        ), patch("builtins.print") as mock_print:
            run_manual_research_dashboard(storage=storage)

        mock_print.assert_any_call(
            "  hypotheses=1, children=0, executable_requests=2, pending_executable_requests=1, completed_results=1"
        )
        mock_print.assert_any_call(
            "- python -m research.runner research-cycle NVDA --run-experiments"
        )


if __name__ == "__main__":
    unittest.main()
