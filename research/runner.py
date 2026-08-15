import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone

from config import settings

from ai.demo_trade_candidate_service import DemoTradeCandidateService
from ai.experiment_request_service import ExperimentRequestService
from ai.hypothesis_revision_application_service import HypothesisRevisionApplicationService
from ai.hypothesis_revision_service import HypothesisRevisionService
from ai.hypothesis_service import HypothesisService
from ai.hypothesis_review_service import HypothesisReviewService
from ai.journal import ResearchJournal
from ai.storage import Storage
from research.executor import ExperimentExecutor
from research.demo_broker_account import check_demo_broker_account
from research.demo_broker_order_status import sync_demo_broker_order_statuses
from research.demo_position_snapshot import sync_demo_position_snapshot
from research.demo_trade_performance_snapshot import build_demo_trade_performance_snapshots
from research.demo_trade_performance_dashboard import build_demo_trade_performance_dashboard
from research.demo_trade_evaluation import EVALUATION_STATUS_ORDER, build_demo_trade_evaluations
from research.demo_hypothesis_performance_summary import (
	SUMMARY_RATING_ORDER,
	build_demo_hypothesis_performance_summaries,
)
from research.demo_promotion_board import (
	BOARD_RECOMMENDATION_ORDER,
	build_demo_promotion_board,
)
from research.demo_current_opportunity_rating import (
	OPPORTUNITY_RATING_ORDER,
	build_demo_current_opportunity_ratings,
)
from research.demo_status_dashboard import build_demo_status_dashboard
from research.demo_exit_readiness import (
	EXIT_READINESS_ORDER,
	build_demo_exit_readiness,
)
from research.demo_ai_review_trigger import (
	TRIGGER_ORDER,
	build_demo_ai_review_trigger,
)
from research.demo_daily_ai_review import (
	build_review_context,
	fingerprint_context,
	new_review_from_payload,
	parse_demo_daily_ai_review,
)
from research.demo_trade_candidate import validate_demo_trade_candidate
from research.demo_broker_readiness import evaluate_demo_broker_readiness
from research.demo_order_intent_add import DemoOrderIntentAddService
from research.demo_paper_order_submit import DemoPaperOrderSubmitService
from research.demo_trade_gate_apply import DemoTradeGateApplyService
from research.demo_trade_gate import DemoTradeGateDecision
from research.demo_trade_gate import evaluate_demo_trade_gate
from research.demo_trade_queue_add import DemoTradeQueueAddService
from research.experiment import ExperimentRequestExecutionState
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.promotion_candidate import PromotionCandidateDecision
from research.promotion_candidate import evaluate_promotion_candidates
from research.research_freshness import ProposalFreshnessStatus
from research.research_freshness import ReviewFreshnessStatus
from research.research_freshness import build_research_freshness
from research.research_plan import ResearchPlanAction
from research.research_plan import ResearchPlanPriority
from research.research_plan import build_research_plan
from research.trade_candidate_proposal import TradeCandidateProposalDecision
from research.trade_candidate_proposal import evaluate_trade_candidate_proposals


DEFAULT_SYMBOL = "NVDA"


def _print_completed_result_metrics(result) -> None:
	def _format_percent(value: float) -> str:
		return f"{value * 100:.2f}%"

	metrics = result.metrics
	metric_lines = []

	if metrics.trade_count is not None:
		metric_lines.append(f"trade_count={metrics.trade_count}")

	if metrics.average_return is not None:
		metric_lines.append(f"average_return={_format_percent(metrics.average_return)}")

	if metrics.win_rate is not None:
		metric_lines.append(f"win_rate={_format_percent(metrics.win_rate)}")

	best_return = metrics.extra_metrics.get("best_return")
	if best_return is not None:
		metric_lines.append(f"best_return={_format_percent(best_return)}")

	worst_return = metrics.extra_metrics.get("worst_return")
	if worst_return is not None:
		metric_lines.append(f"worst_return={_format_percent(worst_return)}")

	if metrics.total_return is not None:
		metric_lines.append(f"total_return={_format_percent(metrics.total_return)}")

	if metric_lines:
		print(f"  metrics: {', '.join(metric_lines)}")


def _print_completed_result_diagnostics(result) -> None:
	metrics = result.metrics
	extra_metrics = metrics.extra_metrics
	diagnostics = getattr(result, "diagnostics", {}) or {}

	rows_loaded = extra_metrics.get("rows_loaded")
	rows_after_cleaning = extra_metrics.get("rows_after_cleaning")
	matching_setups = extra_metrics.get("matching_setups")
	forward_returns_available = extra_metrics.get("forward_returns_available")
	forward_returns_missing = extra_metrics.get("forward_returns_missing")
	forward_horizon = extra_metrics.get("forward_horizon")
	first_match_date = diagnostics.get("first_match_date")
	last_match_date = diagnostics.get("last_match_date")

	diagnostic_values = [
		rows_loaded,
		rows_after_cleaning,
		matching_setups,
		forward_returns_available,
		forward_returns_missing,
		forward_horizon,
		first_match_date,
		last_match_date,
	]

	if all(value is None for value in diagnostic_values):
		return

	def _format_count(value):
		if value is None:
			return "None"

		return str(int(value))

	print(
		"  diagnostics: "
		f"rows_loaded={_format_count(rows_loaded)}, "
		f"rows_after_cleaning={_format_count(rows_after_cleaning)}, "
		f"matching_setups={_format_count(matching_setups)}, "
		f"forward_returns_available={_format_count(forward_returns_available)}, "
		f"forward_returns_missing={_format_count(forward_returns_missing)}, "
		f"forward_horizon={_format_count(forward_horizon)}, "
		f"first_match_date={first_match_date if first_match_date is not None else 'None'}, "
		f"last_match_date={last_match_date if last_match_date is not None else 'None'}"
	)


def run_manual_hypothesis_generation(
	symbol=DEFAULT_SYMBOL,
	sentinel=None,
	journal=None,
	storage=None,
	hypothesis_service=None,
):
	"""Run one-symbol hypothesis generation on demand."""

	if sentinel is None:
		from sentinel.sentinel import Sentinel

		sentinel = Sentinel()

	storage = storage or Storage()
	journal = journal or ResearchJournal()
	journal.storage = storage
	hypothesis_service = hypothesis_service or HypothesisService(storage=storage)

	snapshot = sentinel.get_snapshot(symbol)
	journal_text = journal.build(symbol)
	observations = storage.load_observations(symbol)

	hypotheses = hypothesis_service.generate_for_symbol(
		symbol=symbol,
		journal=journal_text,
		observations=observations,
		snapshot_text=snapshot.to_text(),
	)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Generation: {symbol}")
	print("=" * 50)
	print()
	print(f"Observations Loaded : {len(observations)}")
	print(f"Hypotheses Generated : {len(hypotheses)}")

	if hypotheses:
		print()
		print("Hypotheses")
		print("----------")

		for hypothesis in hypotheses:
			print(
				f"- {hypothesis.title} "
				f"[{hypothesis.status.value}] "
				f"confidence={hypothesis.confidence:.2f}"
			)

	else:
		print()
		print("No hypotheses generated.")

	return hypotheses


def run_manual_experiment_request_generation(
	symbol=DEFAULT_SYMBOL,
	journal=None,
	storage=None,
	experiment_request_service=None,
	planned_only=False,
):
	"""Run one-symbol experiment request generation on demand."""

	storage = storage or Storage()
	journal = journal or ResearchJournal()
	journal.storage = storage
	experiment_request_service = experiment_request_service or ExperimentRequestService(
		storage=storage
	)

	journal_text = journal.build(symbol)
	hypotheses = storage.load_hypotheses(symbol)
	observations = storage.load_observations(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
	hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
	load_revision_applications = getattr(storage, "load_hypothesis_revision_applications", None)
	revision_applications = (
		load_revision_applications(symbol) if callable(load_revision_applications) else []
	)
	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	research_plan = build_research_plan(
		symbol=symbol,
		hypotheses=hypotheses,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		lifecycle_recommendations=lifecycle_recommendations,
		revision_proposals=revision_proposals,
		revision_applications=revision_applications,
	)

	if planned_only:
		planned_hypothesis_ids = {
			item.hypothesis_id
			for item in research_plan.items
			if item.recommended_action == ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST
		}
		selected_hypotheses = [
			hypothesis
			for hypothesis in hypotheses
			if hypothesis.hypothesis_id in planned_hypothesis_ids
		]
		skipped_count = len(hypotheses) - len(selected_hypotheses)
	else:
		selected_hypotheses = hypotheses
		skipped_count = 0

	if planned_only and not selected_hypotheses:
		print()
		print("=" * 50)
		print(f"Manual Experiment Request Generation: {symbol}")
		print("=" * 50)
		print()
		print(f"Hypotheses Loaded : {len(hypotheses)}")
		print("Hypotheses Selected By Plan : 0")
		print(f"Hypotheses Skipped By Plan : {skipped_count}")
		print("Experiment Requests Generated : 0")
		print()
		print("No planned hypotheses selected.")
		return []

	experiment_requests = experiment_request_service.generate_for_symbol(
		symbol=symbol,
		journal=journal_text,
		hypotheses=selected_hypotheses,
		observations=json.dumps(
			[
				{
					"observation_id": observation.observation_id,
					"statement": observation.statement,
				}
				for observation in observations
			],
			indent=4,
		),
	)

	print()
	print("=" * 50)
	print(f"Manual Experiment Request Generation: {symbol}")
	print("=" * 50)
	print()
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	if planned_only:
		print(f"Hypotheses Selected By Plan : {len(selected_hypotheses)}")
		print(f"Hypotheses Skipped By Plan : {skipped_count}")
	print(f"Experiment Requests Generated : {len(experiment_requests)}")

	if experiment_requests:
		print()
		print("Experiment Requests")
		print("-------------------")

		for experiment_request in experiment_requests:
			print(
				f"- {experiment_request.title} "
				f"[{experiment_request.status.value}] "
				f"test_type={experiment_request.test_type.value}"
			)
			print(f"  objective: {experiment_request.objective}")

	else:
		print()
		print("No experiment requests generated.")

	return experiment_requests


def run_manual_research_plan(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic research planning for one symbol."""

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
	hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
	revision_applications = storage.load_hypothesis_revision_applications(symbol)
	revision_applications = storage.load_hypothesis_revision_applications(symbol)
	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	research_plan = build_research_plan(
		symbol=symbol,
		hypotheses=hypotheses,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		lifecycle_recommendations=lifecycle_recommendations,
		revision_proposals=revision_proposals,
		revision_applications=revision_applications,
	)

	print()
	print("=" * 50)
	print(f"Manual Research Plan: {symbol}")
	print("=" * 50)
	print()
	print("Research plan only; no records were modified.")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Plan Items : {len(research_plan.items)}")

	if research_plan.items:
		print()
		print("Research Plan")
		print("-------------")

		for item in research_plan.items:
			print(
				f"- {item.hypothesis_id} action={item.recommended_action.value} priority={item.priority.value}"
			)
			print(f"  reason: {item.reason}")

			if item.related_child_hypothesis_id:
				print(f"  child_hypothesis_id={item.related_child_hypothesis_id}")

			if item.related_proposal_id:
				print(f"  proposal_id={item.related_proposal_id}")

	else:
		print()
		print("No research plan items.")

	return research_plan


def run_manual_research_state(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Render a deterministic read-only research dashboard for one symbol."""

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
	hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
	revision_applications = storage.load_hypothesis_revision_applications(symbol)

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	research_plan = build_research_plan(
		symbol=symbol,
		hypotheses=hypotheses,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		lifecycle_recommendations=lifecycle_recommendations,
		revision_proposals=revision_proposals,
		revision_applications=revision_applications,
	)

	parent_hypothesis_count = sum(
		1
		for hypothesis in hypotheses
		if hypothesis.parent_hypothesis_id is None
	)
	child_hypothesis_count = len(hypotheses) - parent_hypothesis_count
	executable_request_count = sum(
		1
		for request in experiment_requests
		if request.execution_state == ExperimentRequestExecutionState.EXECUTABLE
	)
	completed_result_count = sum(
		1
		for result in experiment_results
		if result.status == ExperimentResultStatus.COMPLETED
	)

	status_counts = {status.value: 0 for status in HypothesisStatus}
	for hypothesis in hypotheses:
		status_counts[hypothesis.status.value] = status_counts.get(hypothesis.status.value, 0) + 1

	evidence_counts = {status.value: 0 for status in HypothesisEvidenceStatus}
	for summary in evidence_summaries:
		evidence_counts[summary.evidence_status.value] = (
			evidence_counts.get(summary.evidence_status.value, 0) + 1
		)

	plan_action_counts = {action.value: 0 for action in ResearchPlanAction}
	for item in research_plan.items:
		plan_action_counts[item.recommended_action.value] = (
			plan_action_counts.get(item.recommended_action.value, 0) + 1
		)

	lineage_pairs = sorted(
		[
			(
				hypothesis.parent_hypothesis_id,
				hypothesis.hypothesis_id,
				hypothesis.source_revision_proposal_id,
			)
			for hypothesis in hypotheses
			if hypothesis.parent_hypothesis_id is not None
		],
	)

	priority_rank = {
		ResearchPlanPriority.HIGH: 0,
		ResearchPlanPriority.MEDIUM: 1,
		ResearchPlanPriority.LOW: 2,
	}
	attention_items = sorted(
		enumerate(research_plan.items),
		key=lambda entry: (priority_rank.get(entry[1].priority, 99), entry[0]),
	)

	print()
	print("=" * 50)
	print(f"Manual Research State: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")

	print()
	print("Object Counts")
	print("-------------")
	print(f"- hypotheses : {len(hypotheses)}")
	print(f"- parent hypotheses : {parent_hypothesis_count}")
	print(f"- child hypotheses : {child_hypothesis_count}")
	print(f"- experiment requests : {len(experiment_requests)}")
	print(f"- executable experiment requests : {executable_request_count}")
	print(f"- completed experiment results : {completed_result_count}")
	print(f"- hypothesis reviews : {len(hypothesis_reviews)}")
	print(f"- revision proposals : {len(revision_proposals)}")
	print(f"- revision applications : {len(revision_applications)}")
	print(f"- research plan items : {len(research_plan.items)}")

	print()
	print("Hypothesis Status Summary")
	print("-------------------------")
	for status in HypothesisStatus:
		print(f"- {status.value} : {status_counts.get(status.value, 0)}")

	print()
	print("Evidence Summary")
	print("----------------")
	for status in HypothesisEvidenceStatus:
		print(f"- {status.value} : {evidence_counts.get(status.value, 0)}")

	print()
	print("Research Plan Summary")
	print("---------------------")
	for action in ResearchPlanAction:
		print(f"- {action.value} : {plan_action_counts.get(action.value, 0)}")

	print()
	print("Lineage Summary")
	print("---------------")
	if lineage_pairs:
		for parent_hypothesis_id, child_hypothesis_id, source_revision_proposal_id in lineage_pairs:
			if source_revision_proposal_id:
				print(
					"- "
					f"parent_hypothesis_id={parent_hypothesis_id} "
					f"child_hypothesis_id={child_hypothesis_id} "
					f"source_revision_proposal_id={source_revision_proposal_id}"
				)
			else:
				print(
					"- "
					f"parent_hypothesis_id={parent_hypothesis_id} "
					f"child_hypothesis_id={child_hypothesis_id}"
				)
	else:
		print("No parent-child hypothesis lineage records found.")

	print()
	print("Top Attention Items")
	print("-------------------")
	if attention_items:
		for _, item in attention_items[:5]:
			print(
				"- "
				f"hypothesis_id={item.hypothesis_id} "
				f"action={item.recommended_action.value} "
				f"priority={item.priority.value}"
			)
			print(f"  reason: {item.reason}")
	else:
		print("No research plan attention items.")

	print()
	print("Research state read complete. No records were modified.")

	return research_plan


def run_manual_research_freshness(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Render a deterministic read-only freshness report for one symbol."""

	def _format_timestamp(value):
		if value is None:
			return "None"
		if isinstance(value, str):
			return value

		return value.isoformat()

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	observations = storage.load_observations(symbol)
	load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
	hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
	revision_applications = storage.load_hypothesis_revision_applications(symbol)

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	research_plan = build_research_plan(
		symbol=symbol,
		hypotheses=hypotheses,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		lifecycle_recommendations=lifecycle_recommendations,
		revision_proposals=revision_proposals,
		revision_applications=revision_applications,
	)
	freshness_items = build_research_freshness(
		hypotheses=hypotheses,
		observations=observations,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		hypothesis_reviews=hypothesis_reviews,
		revision_proposals=revision_proposals,
		lifecycle_recommendations=lifecycle_recommendations,
	)

	review_freshness_counts = {status.value: 0 for status in ReviewFreshnessStatus}
	for item in freshness_items:
		review_freshness_counts[item.review_freshness.value] = (
			review_freshness_counts.get(item.review_freshness.value, 0) + 1
		)

	print()
	print("=" * 50)
	print(f"Manual Research Freshness: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Freshness Items : {len(freshness_items)}")

	print()
	print("Research Freshness")
	print("------------------")
	for item in freshness_items:
		print(
			f"- {item.hypothesis_id} "
			f"review_freshness={item.review_freshness.value} "
			f"proposal_freshness={item.proposal_freshness.value}"
		)
		print(f"  latest_completed_result_at={_format_timestamp(item.latest_completed_result_at)}")
		print(f"  latest_review_at={_format_timestamp(item.latest_review_at)}")
		print(f"  latest_observation_at={_format_timestamp(item.latest_observation_at)}")
		print(f"  latest_revision_proposal_at={_format_timestamp(item.latest_revision_proposal_at)}")
		print(f"  rationale: {item.rationale}")

	print()
	print("Freshness Summary")
	print("-----------------")
	for status in ReviewFreshnessStatus:
		print(f"- {status.value} : {review_freshness_counts.get(status.value, 0)}")

	print()
	print("Suggested Next Commands")
	print("-----------------------")
	suggestions = []
	review_issue_hypothesis_ids = {
		item.hypothesis_id
		for item in freshness_items
		if item.review_freshness in {
			ReviewFreshnessStatus.MISSING,
			ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT,
			ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION,
		}
	}
	proposal_issue_hypothesis_ids = {
		item.hypothesis_id
		for item in freshness_items
		if item.proposal_freshness in {
			ProposalFreshnessStatus.MISSING_FOR_REFINE_CANDIDATE,
			ProposalFreshnessStatus.STALE_AFTER_REVIEW,
		}
	}
	actionable_review_hypothesis_ids = {
		item.hypothesis_id
		for item in research_plan.items
		if item.recommended_action == ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW
	}
	actionable_revision_hypothesis_ids = {
		item.hypothesis_id
		for item in research_plan.items
		if item.recommended_action == ResearchPlanAction.GENERATE_REVISION_PROPOSAL
	}
	actionable_review_issue_hypothesis_ids = (
		review_issue_hypothesis_ids & actionable_review_hypothesis_ids
	)
	actionable_proposal_issue_hypothesis_ids = (
		proposal_issue_hypothesis_ids & actionable_revision_hypothesis_ids
	)

	if actionable_review_issue_hypothesis_ids:
		suggestions.append(f"python -m research.runner research-cycle {symbol} --reviews")

	if actionable_proposal_issue_hypothesis_ids:
		suggestions.append(f"python -m research.runner research-cycle {symbol} --revisions")

	has_freshness_issues = bool(review_issue_hypothesis_ids or proposal_issue_hypothesis_ids)
	has_actionable_freshness_command = bool(
		actionable_review_issue_hypothesis_ids or actionable_proposal_issue_hypothesis_ids
	)

	if suggestions:
		for suggestion in suggestions:
			print(f"- {suggestion}")

		if has_freshness_issues and not has_actionable_freshness_command:
			print("Freshness issues exist, but no automatic research-cycle action is currently eligible.")
	else:
		if has_freshness_issues and not has_actionable_freshness_command:
			print("Freshness issues exist, but no automatic research-cycle action is currently eligible.")
		else:
			print("No suggested follow-up commands from current freshness state.")

	print()
	print("Research freshness read complete. No records were modified.")

	return freshness_items


def run_manual_research_dashboard(
	symbols=None,
	storage=None,
):
	"""Render a deterministic read-only research dashboard for multiple symbols."""

	storage = storage or Storage()

	if symbols:
		reviewed_symbols = list(symbols)
	else:
		reviewed_symbols = list(settings.WATCHLIST)

	priority_rank = {
		ResearchPlanPriority.HIGH: 0,
		ResearchPlanPriority.MEDIUM: 1,
		ResearchPlanPriority.LOW: 2,
	}

	action_order = [action.value for action in ResearchPlanAction]
	aggregated_action_counts = {action: 0 for action in action_order}
	attention_items = []
	symbol_summaries = []
	suggested_commands = []
	suggested_command_set = set()
	has_any_freshness_issues = False
	has_any_actionable_freshness_command = False

	def _add_suggested_command(command):
		if command in suggested_command_set:
			return

		suggested_command_set.add(command)
		suggested_commands.append(command)

	def _completed_request_ids_for_results(experiment_results):
		return {
			result.experiment_request_id
			for result in experiment_results
			if result.status == ExperimentResultStatus.COMPLETED and result.experiment_request_id
		}

	for symbol in reviewed_symbols:
		hypotheses = storage.load_hypotheses(symbol)
		observations = storage.load_observations(symbol)
		experiment_requests = storage.load_experiment_requests(symbol)
		experiment_results = storage.load_experiment_results(symbol)
		load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
		hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
		revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
		revision_applications = storage.load_hypothesis_revision_applications(symbol)

		evidence_summaries = evaluate_hypothesis_evidence(
			hypotheses=hypotheses,
			experiment_results=experiment_results,
			experiment_requests=experiment_requests,
		)
		latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
		lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
			hypotheses=hypotheses,
			evidence_summaries=evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		)
		research_plan = build_research_plan(
			symbol=symbol,
			hypotheses=hypotheses,
			experiment_requests=experiment_requests,
			experiment_results=experiment_results,
			evidence_summaries=evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
			lifecycle_recommendations=lifecycle_recommendations,
			revision_proposals=revision_proposals,
			revision_applications=revision_applications,
		)
		freshness_items = build_research_freshness(
			hypotheses=hypotheses,
			observations=observations,
			experiment_requests=experiment_requests,
			experiment_results=experiment_results,
			hypothesis_reviews=hypothesis_reviews,
			revision_proposals=revision_proposals,
			lifecycle_recommendations=lifecycle_recommendations,
		)
		stale_review_count = sum(
			1
			for item in freshness_items
			if item.review_freshness in {
				ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT,
				ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION,
			}
		)
		missing_review_count = sum(
			1 for item in freshness_items if item.review_freshness == ReviewFreshnessStatus.MISSING
		)
		stale_revision_proposal_count = sum(
			1 for item in freshness_items if item.proposal_freshness == ProposalFreshnessStatus.STALE_AFTER_REVIEW
		)
		missing_revision_proposal_count = sum(
			1
			for item in freshness_items
			if item.proposal_freshness == ProposalFreshnessStatus.MISSING_FOR_REFINE_CANDIDATE
		)
		review_issue_hypothesis_ids = {
			item.hypothesis_id
			for item in freshness_items
			if item.review_freshness in {
				ReviewFreshnessStatus.MISSING,
				ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT,
				ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION,
			}
		}
		proposal_issue_hypothesis_ids = {
			item.hypothesis_id
			for item in freshness_items
			if item.proposal_freshness in {
				ProposalFreshnessStatus.MISSING_FOR_REFINE_CANDIDATE,
				ProposalFreshnessStatus.STALE_AFTER_REVIEW,
			}
		}
		if review_issue_hypothesis_ids or proposal_issue_hypothesis_ids:
			has_any_freshness_issues = True

		child_hypothesis_count = sum(
			1
			for hypothesis in hypotheses
			if hypothesis.parent_hypothesis_id is not None
		)
		executable_request_count = sum(
			1
			for request in experiment_requests
			if request.execution_state == ExperimentRequestExecutionState.EXECUTABLE
		)
		completed_request_ids = _completed_request_ids_for_results(experiment_results)
		pending_executable_request_count = sum(
			1
			for request in experiment_requests
			if request.execution_state == ExperimentRequestExecutionState.EXECUTABLE
			and request.experiment_request_id not in completed_request_ids
		)
		completed_result_count = sum(
			1
			for result in experiment_results
			if result.status == ExperimentResultStatus.COMPLETED
		)

		per_symbol_action_counts = {action: 0 for action in action_order}
		for item in research_plan.items:
			per_symbol_action_counts[item.recommended_action.value] = (
				per_symbol_action_counts.get(item.recommended_action.value, 0) + 1
			)
			aggregated_action_counts[item.recommended_action.value] = (
				aggregated_action_counts.get(item.recommended_action.value, 0) + 1
			)
			attention_items.append(item)

		highest_priority = "none"
		if research_plan.items:
			highest_priority_item = min(
				research_plan.items,
				key=lambda item: priority_rank.get(item.priority, 99),
			)
			highest_priority = highest_priority_item.priority.value

		top_action = "none"
		if research_plan.items:
			for action_value in action_order:
				if per_symbol_action_counts[action_value] == max(per_symbol_action_counts.values()):
					top_action = action_value
					break

		symbol_summaries.append(
			{
				"symbol": symbol,
				"hypotheses": len(hypotheses),
				"children": child_hypothesis_count,
				"executable_requests": executable_request_count,
				"pending_executable_requests": pending_executable_request_count,
				"completed_results": completed_result_count,
				"reviews": len(hypothesis_reviews),
				"revision_proposals": len(revision_proposals),
				"stale_reviews": stale_review_count,
				"missing_reviews": missing_review_count,
				"stale_revision_proposals": stale_revision_proposal_count,
				"missing_revision_proposals": missing_revision_proposal_count,
				"plan_items": len(research_plan.items),
				"highest_priority": highest_priority,
				"top_action": top_action,
				"action_counts": per_symbol_action_counts,
			}
		)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST.value] > 0:
			_add_suggested_command(
				f"python -m research.runner research-cycle {symbol} --planned-experiments"
			)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW.value] > 0:
			_add_suggested_command(
				f"python -m research.runner research-cycle {symbol} --reviews"
			)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_REVISION_PROPOSAL.value] > 0:
			_add_suggested_command(
				f"python -m research.runner research-cycle {symbol} --revisions"
			)

		if pending_executable_request_count > 0:
			_add_suggested_command(
				f"python -m research.runner research-cycle {symbol} --run-experiments"
			)

		if per_symbol_action_counts[ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE.value] > 0:
			_add_suggested_command(
				f"python -m research.runner hypothesis-revision-apply {symbol} <proposal_id> --dry-run"
			)
		actionable_review_hypothesis_ids = {
			item.hypothesis_id
			for item in research_plan.items
			if item.recommended_action == ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW
		}
		actionable_revision_hypothesis_ids = {
			item.hypothesis_id
			for item in research_plan.items
			if item.recommended_action == ResearchPlanAction.GENERATE_REVISION_PROPOSAL
		}

		if review_issue_hypothesis_ids & actionable_review_hypothesis_ids:
			_add_suggested_command(f"python -m research.runner research-cycle {symbol} --reviews")
			has_any_actionable_freshness_command = True

		if proposal_issue_hypothesis_ids & actionable_revision_hypothesis_ids:
			_add_suggested_command(f"python -m research.runner research-cycle {symbol} --revisions")
			has_any_actionable_freshness_command = True

	sorted_attention_items = sorted(
		attention_items,
		key=lambda item: (
			priority_rank.get(item.priority, 99),
			item.symbol,
			item.hypothesis_id,
			item.recommended_action.value,
		),
	)

	print()
	print("=" * 50)
	print("Manual Research Dashboard")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Symbols Reviewed : {len(reviewed_symbols)}")

	print()
	print("Per-Symbol Summary")
	print("------------------")
	for summary in symbol_summaries:
		print(f"- {summary['symbol']}")
		print(
			"  hypotheses="
			f"{summary['hypotheses']}, "
			f"children={summary['children']}, "
			f"executable_requests={summary['executable_requests']}, "
			f"pending_executable_requests={summary['pending_executable_requests']}, "
			f"completed_results={summary['completed_results']}"
		)
		print(
			"  reviews="
			f"{summary['reviews']}, "
			f"revision_proposals={summary['revision_proposals']}, "
			f"stale_reviews={summary['stale_reviews']}, "
			f"missing_reviews={summary['missing_reviews']}, "
			f"stale_revision_proposals={summary['stale_revision_proposals']}, "
			f"missing_revision_proposals={summary['missing_revision_proposals']}, "
			f"plan_items={summary['plan_items']}"
		)
		print(f"  highest_priority={summary['highest_priority']}")
		print(f"  top_action={summary['top_action']}")

	print()
	print("Watchlist Action Summary")
	print("------------------------")
	for action_value in action_order:
		print(f"- {action_value} : {aggregated_action_counts.get(action_value, 0)}")

	print()
	print("Attention Queue")
	print("---------------")
	if sorted_attention_items:
		for item in sorted_attention_items[:10]:
			print(
				"- "
				f"symbol={item.symbol} "
				f"hypothesis_id={item.hypothesis_id} "
				f"action={item.recommended_action.value} "
				f"priority={item.priority.value}"
			)
			print(f"  reason: {item.reason}")
	else:
		print("No attention items found across reviewed symbols.")

	print()
	print("Suggested Next Commands")
	print("-----------------------")
	if suggested_commands:
		for command in suggested_commands:
			print(f"- {command}")

		if has_any_freshness_issues and not has_any_actionable_freshness_command:
			print("Freshness issues exist, but no automatic research-cycle action is currently eligible.")

		if any(
			summary["action_counts"][ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE.value] > 0
			for summary in symbol_summaries
		):
			print(
				"- Note: hypothesis-revision-apply requires a concrete proposal_id and explicit human choice."
			)
	else:
		if has_any_freshness_issues and not has_any_actionable_freshness_command:
			print("Freshness issues exist, but no automatic research-cycle action is currently eligible.")
		else:
			print("No suggested follow-up commands from current watchlist state.")

	print()
	print("Research dashboard read complete. No records were modified.")

	return symbol_summaries


def run_manual_research_cycle(
	symbol=DEFAULT_SYMBOL,
	dry_run=True,
	reviews=False,
	planned_experiments=False,
	run_experiments=False,
	revisions=False,
	full_safe=False,
	period=settings.BACKTEST_PERIOD,
	interval=settings.BACKTEST_INTERVAL,
	storage=None,
	hypothesis_review_service=None,
	hypothesis_revision_service=None,
	experiment_request_service=None,
	executor=None,
	journal=None,
):
	"""Run a manual research cycle in one explicit orchestration mode."""

	selected_modes = [
		dry_run,
		reviews,
		planned_experiments,
		run_experiments,
		revisions,
		full_safe,
	]
	if sum(1 for enabled in selected_modes if enabled) != 1:
		raise ValueError(
			"research-cycle mode is mutually exclusive: choose exactly one of dry-run, reviews, planned-experiments, run-experiments, revisions, or full-safe"
		)

	storage = storage or Storage()

	def _build_cycle_state():
		hypotheses = storage.load_hypotheses(symbol)
		experiment_requests = storage.load_experiment_requests(symbol)
		experiment_results = storage.load_experiment_results(symbol)
		load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
		hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
		revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
		revision_applications = storage.load_hypothesis_revision_applications(symbol)
		evidence_summaries = evaluate_hypothesis_evidence(
			hypotheses=hypotheses,
			experiment_results=experiment_results,
			experiment_requests=experiment_requests,
		)
		latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
		lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
			hypotheses=hypotheses,
			evidence_summaries=evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		)
		research_plan = build_research_plan(
			symbol=symbol,
			hypotheses=hypotheses,
			experiment_requests=experiment_requests,
			experiment_results=experiment_results,
			evidence_summaries=evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
			lifecycle_recommendations=lifecycle_recommendations,
			revision_proposals=revision_proposals,
			revision_applications=revision_applications,
		)

		return {
			"hypotheses": hypotheses,
			"experiment_requests": experiment_requests,
			"experiment_results": experiment_results,
			"hypothesis_reviews": hypothesis_reviews,
			"revision_proposals": revision_proposals,
			"revision_applications": revision_applications,
			"evidence_summaries": evidence_summaries,
			"latest_reviews_by_hypothesis_id": latest_reviews_by_hypothesis_id,
			"lifecycle_recommendations": lifecycle_recommendations,
			"research_plan": research_plan,
		}

	state = _build_cycle_state()
	hypotheses = state["hypotheses"]
	experiment_requests = state["experiment_requests"]
	experiment_results = state["experiment_results"]
	evidence_summaries = state["evidence_summaries"]
	latest_reviews_by_hypothesis_id = state["latest_reviews_by_hypothesis_id"]
	research_plan = state["research_plan"]
	planned_action_counts = {}
	for item in research_plan.items:
		planned_action_counts[item.recommended_action.value] = planned_action_counts.get(item.recommended_action.value, 0) + 1

	review_candidate_hypothesis_ids = {
		item.hypothesis_id
		for item in research_plan.items
		if item.recommended_action == ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW
	}
	review_candidates = [
		hypothesis
		for hypothesis in hypotheses
		if hypothesis.hypothesis_id in review_candidate_hypothesis_ids
	]

	if reviews:
		reviews_generated = []
		final_plan = research_plan

		print()
		print("=" * 50)
		print(f"Manual Research Cycle: {symbol}")
		print("=" * 50)
		print()
		print("Mode : reviews")
		print("Records Modified : yes")
		print("AI Calls Allowed : yes")
		print(f"Hypotheses Loaded : {len(hypotheses)}")
		print(f"Review Candidates : {len(review_candidates)}")

		if review_candidates:
			hypothesis_review_service = (
				hypothesis_review_service
				or HypothesisReviewService(storage=storage)
			)

			try:
				reviews_generated = hypothesis_review_service.generate_for_symbol(
					symbol=symbol,
					hypotheses=review_candidates,
				)
			except TypeError:
				# Backward-compatible fallback if a custom service does not accept scoped hypotheses.
				reviews_generated = hypothesis_review_service.generate_for_symbol(symbol=symbol)

			state = _build_cycle_state()
			final_plan = state["research_plan"]

			print(f"Reviews Generated : {len(reviews_generated)}")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : completed")
		else:
			print("Reviews Generated : 0")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : no-op")
			print()
			print("No-op: no hypotheses currently require review generation.")

		return final_plan

	planned_experiment_hypothesis_ids = {
		item.hypothesis_id
		for item in research_plan.items
		if item.recommended_action == ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST
	}
	planned_experiment_candidates = [
		hypothesis
		for hypothesis in hypotheses
		if hypothesis.hypothesis_id in planned_experiment_hypothesis_ids
	]

	if planned_experiments:
		final_plan = research_plan
		hypotheses_skipped_count = len(hypotheses) - len(planned_experiment_candidates)

		print()
		print("=" * 50)
		print(f"Manual Research Cycle: {symbol}")
		print("=" * 50)
		print()
		print("Mode : planned-experiments")
		print("Records Modified : yes")
		print("AI Calls Allowed : yes")
		print(f"Hypotheses Loaded : {len(hypotheses)}")
		print(f"Hypotheses Selected By Plan : {len(planned_experiment_candidates)}")
		print(f"Hypotheses Skipped By Plan : {hypotheses_skipped_count}")

		if planned_experiment_candidates:
			journal = journal or ResearchJournal()
			journal.storage = storage
			experiment_request_service = experiment_request_service or ExperimentRequestService(
				storage=storage
			)
			observations = storage.load_observations(symbol)
			generated_requests = experiment_request_service.generate_for_symbol(
				symbol=symbol,
				journal=journal.build(symbol),
				hypotheses=planned_experiment_candidates,
				observations=json.dumps(
					[
						{
							"observation_id": observation.observation_id,
							"statement": observation.statement,
						}
						for observation in observations
					],
					indent=4,
				),
			)

			state = _build_cycle_state()
			final_plan = state["research_plan"]

			print(f"Experiment Requests Generated : {len(generated_requests)}")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : completed")
		else:
			print("Experiment Requests Generated : 0")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : no-op")
			print()
			print("No-op: no hypotheses currently require planned experiment requests.")

		return final_plan

	if run_experiments:
		executor = executor or ExperimentExecutor()
		execution_summary = _execute_experiment_requests_for_symbol(
			symbol=symbol,
			storage=storage,
			executor=executor,
			period=period,
			interval=interval,
		)

		state = _build_cycle_state()
		final_plan = state["research_plan"]

		print()
		print("=" * 50)
		print(f"Manual Research Cycle: {symbol}")
		print("=" * 50)
		print()
		print("Mode : run-experiments")
		print("Records Modified : yes")
		print("AI Calls Allowed : no")
		print(f"Requests Loaded : {execution_summary['requests_loaded']}")
		print(f"Requests Executed : {execution_summary['requests_executed']}")
		print(f"Requests Skipped : {execution_summary['requests_skipped']}")
		print(f"Backtest Period : {period}")
		print(f"Backtest Interval : {interval}")
		print(f"Results Saved : {execution_summary['results_saved']}")
		print(f"Not Implemented : {execution_summary['not_implemented']}")
		print(f"Research Plan Items : {len(final_plan.items)}")

		if execution_summary["requests_executed"] == 0:
			print("Final Status : no-op")
			print()
			print("No-op: no executable experiment requests currently available for this symbol.")
		else:
			print("Final Status : completed")

		return final_plan

	revision_candidate_hypothesis_ids = {
		item.hypothesis_id
		for item in research_plan.items
		if item.recommended_action == ResearchPlanAction.GENERATE_REVISION_PROPOSAL
	}
	revision_candidates = [
		hypothesis
		for hypothesis in hypotheses
		if hypothesis.hypothesis_id in revision_candidate_hypothesis_ids
	]

	if revisions:
		generated_proposals = []
		final_plan = research_plan

		print()
		print("=" * 50)
		print(f"Manual Research Cycle: {symbol}")
		print("=" * 50)
		print()
		print("Mode : revisions")
		print("Records Modified : yes")
		print("AI Calls Allowed : yes")
		print(f"Hypotheses Loaded : {len(hypotheses)}")
		print(f"Revision Candidates : {len(revision_candidates)}")

		if revision_candidates:
			hypothesis_revision_service = (
				hypothesis_revision_service
				or HypothesisRevisionService(storage=storage)
			)

			try:
				generated_proposals = hypothesis_revision_service.generate_for_symbol(
					symbol=symbol,
					hypotheses=revision_candidates,
				)
			except TypeError:
				# Backward-compatible fallback if a custom service does not accept scoped hypotheses.
				generated_proposals = hypothesis_revision_service.generate_for_symbol(symbol=symbol)

			state = _build_cycle_state()
			final_plan = state["research_plan"]
			print(f"Revision Proposals Generated : {len(generated_proposals)}")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : completed")
		else:
			print("Revision Proposals Generated : 0")
			print(f"Research Plan Items : {len(final_plan.items)}")
			print("Final Status : no-op")
			print()
			print("No-op: no hypotheses currently require revision proposal generation.")

		return final_plan

	if full_safe:
		current_state = state
		current_plan = current_state["research_plan"]

		planned_candidates = [
			hypothesis
			for hypothesis in current_state["hypotheses"]
			if hypothesis.hypothesis_id in {
				item.hypothesis_id
				for item in current_plan.items
				if item.recommended_action == ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST
			}
		]
		review_candidates = []
		revision_candidates = []
		generated_requests = []
		generated_reviews = []
		generated_proposals = []
		step_failures = []
		execution_summary = {
			"requests_loaded": 0,
			"requests_executed": 0,
			"requests_skipped": 0,
			"results_saved": 0,
			"not_implemented": 0,
		}

		# Step 2: generate planned experiment requests.
		if planned_candidates:
			try:
				journal = journal or ResearchJournal()
				journal.storage = storage
				experiment_request_service = experiment_request_service or ExperimentRequestService(
					storage=storage
				)
				observations = storage.load_observations(symbol)
				generated_requests = experiment_request_service.generate_for_symbol(
					symbol=symbol,
					journal=journal.build(symbol),
					hypotheses=planned_candidates,
					observations=json.dumps(
						[
							{
								"observation_id": observation.observation_id,
								"statement": observation.statement,
							}
							for observation in observations
						],
						indent=4,
					),
				)
			except Exception as exc:
				step_failures.append(
					"Step 2 failed (planned experiment request generation): "
					f"{exc.__class__.__name__}: {exc}"
				)

		# Step 3: execute currently executable experiment requests.
		try:
			executor = executor or ExperimentExecutor()
			execution = _execute_experiment_requests_for_symbol(
				symbol=symbol,
				storage=storage,
				executor=executor,
				period=period,
				interval=interval,
			)
			execution_summary = {
				"requests_loaded": execution["requests_loaded"],
				"requests_executed": execution["requests_executed"],
				"requests_skipped": execution["requests_skipped"],
				"results_saved": execution["results_saved"],
				"not_implemented": execution["not_implemented"],
			}
		except Exception as exc:
			step_failures.append(
				"Step 3 failed (experiment execution): "
				f"{exc.__class__.__name__}: {exc}"
			)

		# Step 4: rebuild evidence and research plan.
		try:
			current_state = _build_cycle_state()
			current_plan = current_state["research_plan"]
		except Exception as exc:
			step_failures.append(
				"Step 4 failed (post-execution plan rebuild): "
				f"{exc.__class__.__name__}: {exc}"
			)

		# Step 5: generate reviews for plan-selected hypotheses.
		review_candidates = [
			hypothesis
			for hypothesis in current_state["hypotheses"]
			if hypothesis.hypothesis_id in {
				item.hypothesis_id
				for item in current_plan.items
				if item.recommended_action == ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW
			}
		]
		if review_candidates:
			try:
				hypothesis_review_service = (
					hypothesis_review_service
					or HypothesisReviewService(storage=storage)
				)
				try:
					generated_reviews = hypothesis_review_service.generate_for_symbol(
						symbol=symbol,
						hypotheses=review_candidates,
					)
				except TypeError:
					generated_reviews = hypothesis_review_service.generate_for_symbol(symbol=symbol)
			except Exception as exc:
				step_failures.append(
					"Step 5 failed (hypothesis review generation): "
					f"{exc.__class__.__name__}: {exc}"
				)

		# Step 6: rebuild lifecycle recommendations and plan.
		try:
			current_state = _build_cycle_state()
			current_plan = current_state["research_plan"]
		except Exception as exc:
			step_failures.append(
				"Step 6 failed (post-review plan rebuild): "
				f"{exc.__class__.__name__}: {exc}"
			)

		# Step 7: generate revision proposals for plan-selected hypotheses.
		revision_candidates = [
			hypothesis
			for hypothesis in current_state["hypotheses"]
			if hypothesis.hypothesis_id in {
				item.hypothesis_id
				for item in current_plan.items
				if item.recommended_action == ResearchPlanAction.GENERATE_REVISION_PROPOSAL
			}
		]
		if revision_candidates:
			try:
				hypothesis_revision_service = (
					hypothesis_revision_service
					or HypothesisRevisionService(storage=storage)
				)
				try:
					generated_proposals = hypothesis_revision_service.generate_for_symbol(
						symbol=symbol,
						hypotheses=revision_candidates,
					)
				except TypeError:
					generated_proposals = hypothesis_revision_service.generate_for_symbol(
						symbol=symbol
					)
			except Exception as exc:
				step_failures.append(
					"Step 7 failed (revision proposal generation): "
					f"{exc.__class__.__name__}: {exc}"
				)

		# Step 8: final research plan rebuild.
		try:
			current_state = _build_cycle_state()
			current_plan = current_state["research_plan"]
		except Exception as exc:
			step_failures.append(
				"Step 8 failed (final plan rebuild): "
				f"{exc.__class__.__name__}: {exc}"
			)

		print()
		print("=" * 50)
		print(f"Manual Research Cycle: {symbol}")
		print("=" * 50)
		print()
		print("Mode : full-safe")
		print("Records Modified : yes")
		print("AI Calls Allowed : yes")
		print(f"Initial Research Plan Items : {len(research_plan.items)}")
		print(f"Planned Experiment Candidates : {len(planned_candidates)}")
		print(f"Experiment Requests Generated : {len(generated_requests)}")
		print(f"Backtest Period : {period}")
		print(f"Backtest Interval : {interval}")
		print(f"Requests Executed : {execution_summary['requests_executed']}")
		print(f"Results Saved : {execution_summary['results_saved']}")
		print(f"Review Candidates : {len(review_candidates)}")
		print(f"Reviews Generated : {len(generated_reviews)}")
		print(f"Revision Candidates : {len(revision_candidates)}")
		print(f"Revision Proposals Generated : {len(generated_proposals)}")
		print(f"Final Research Plan Items : {len(current_plan.items)}")

		if step_failures:
			print("Final Status : completed_with_step_failures")
			print()
			print("Step Failures")
			print("-------------")
			for failure in step_failures:
				print(f"- {failure}")
		else:
			print("Final Status : completed")

		print()
		print("Safety Summary")
		print("--------------")
		print("- No hypotheses were mutated.")
		print("- No revision proposals were applied.")
		print("- No child hypotheses were created.")
		print("- No trades were created or executed.")
		print("Revision proposals are not applied automatically.")

		return current_plan

	print()
	print("=" * 50)
	print(f"Manual Research Cycle: {symbol}")
	print("=" * 50)
	print()
	print("Mode : dry-run")
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Experiment Requests Loaded : {len(experiment_requests)}")
	print(f"Completed Results Loaded : {sum(1 for result in experiment_results if result.status == ExperimentResultStatus.COMPLETED)}")
	print(f"Research Plan Items : {len(research_plan.items)}")

	print()
	print("Planned Actions")
	print("---------------")
	for action in ResearchPlanAction:
		print(f"- {action.value} : {planned_action_counts.get(action.value, 0)}")

	print()
	print("Research Plan")
	print("-------------")
	if research_plan.items:
		for item in research_plan.items:
			print(
				f"- {item.hypothesis_id} action={item.recommended_action.value} priority={item.priority.value}"
			)
			print(f"  reason: {item.reason}")
			if item.related_child_hypothesis_id:
				print(f"  child_hypothesis_id={item.related_child_hypothesis_id}")
			if item.related_proposal_id:
				print(f"  proposal_id={item.related_proposal_id}")
	else:
		print("No research plan items.")

	print()
	print("Dry run complete. No records were modified.")

	return research_plan


def run_manual_experiment_execution(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	executor=None,
	period=settings.BACKTEST_PERIOD,
	interval=settings.BACKTEST_INTERVAL,
):
	"""Run one-symbol experiment execution on demand using stored requests."""

	storage = storage or Storage()
	executor = executor or ExperimentExecutor()
	execution_summary = _execute_experiment_requests_for_symbol(
		symbol=symbol,
		storage=storage,
		executor=executor,
		period=period,
		interval=interval,
	)
	experiment_results = execution_summary["experiment_results"]

	print()
	print("=" * 50)
	print(f"Manual Experiment Execution: {symbol}")
	print("=" * 50)
	print()
	print(f"Requests Loaded : {execution_summary['requests_loaded']}")
	print(f"Requests Executed : {execution_summary['requests_executed']}")
	print(f"Requests Skipped : {execution_summary['requests_skipped']}")
	print(f"Backtest Period : {period}")
	print(f"Backtest Interval : {interval}")
	print(f"Skipped Non-Executable : {execution_summary['skipped_non_executable']}")
	print(f"Skipped Obsolete : {execution_summary['skipped_obsolete']}")
	print(f"Skipped Symbol Mismatch : {execution_summary['skipped_symbol_mismatch']}")
	print(f"Results Saved : {execution_summary['results_saved']}")
	print(f"Not Implemented : {execution_summary['not_implemented']}")

	if experiment_results:
		print()
		print("Experiment Results")
		print("------------------")

		for result in experiment_results:
			print(
				f"- {result.test_type.value} "
				f"[{result.status.value}] "
				f"request_id={result.experiment_request_id} "
				f"result_id={result.experiment_result_id}"
			)

			if result.failure_reason:
				print(f"  reason: {result.failure_reason}")
			elif result.summary:
				print(f"  summary: {result.summary}")

			if result.status == ExperimentResultStatus.COMPLETED:
				_print_completed_result_metrics(result)
				_print_completed_result_diagnostics(result)

	else:
		print()
		print("No experiment requests to execute.")

	return experiment_results


def _execute_experiment_requests_for_symbol(
	symbol,
	storage,
	executor,
	period,
	interval,
):
	"""Execute currently executable requests and return deterministic execution counts."""

	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = []
	skipped_symbol_mismatch_count = 0
	skipped_non_executable_count = 0
	skipped_obsolete_count = 0

	for request in experiment_requests:
		if request.symbol and request.symbol != symbol:
			skipped_symbol_mismatch_count += 1
			continue

		if request.execution_state == ExperimentRequestExecutionState.OBSOLETE:
			skipped_obsolete_count += 1
			continue

		if request.execution_state == ExperimentRequestExecutionState.NON_EXECUTABLE:
			skipped_non_executable_count += 1
			continue

		experiment_results.append(
			executor.execute(request, period=period, interval=interval)
		)

	if experiment_results:
		storage.save_experiment_results(symbol, experiment_results)

	not_implemented_count = sum(
		1
		for result in experiment_results
		if result.status == ExperimentResultStatus.NOT_IMPLEMENTED
	)
	total_skipped_count = (
		skipped_symbol_mismatch_count
		+ skipped_non_executable_count
		+ skipped_obsolete_count
	)

	return {
		"experiment_results": experiment_results,
		"requests_loaded": len(experiment_requests),
		"requests_executed": len(experiment_results),
		"requests_skipped": total_skipped_count,
		"skipped_non_executable": skipped_non_executable_count,
		"skipped_obsolete": skipped_obsolete_count,
		"skipped_symbol_mismatch": skipped_symbol_mismatch_count,
		"results_saved": len(experiment_results),
		"not_implemented": not_implemented_count,
	}


def run_manual_hypothesis_evaluation(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic hypothesis evidence summarization for one symbol."""

	def _format_percent(value):
		if value is None:
			return "n/a"

		return f"{value * 100:.2f}%"

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)

	evaluations = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)

	completed_results_count = sum(
		1
		for result in experiment_results
		if result.status == ExperimentResultStatus.COMPLETED
	)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Evaluation: {symbol}")
	print("=" * 50)
	print()
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Completed Results Loaded : {completed_results_count}")
	print(f"Hypotheses Evaluated : {len(evaluations)}")

	if evaluations:
		print()
		print("Hypothesis Evidence")
		print("-------------------")

		for evaluation in evaluations:
			print(
				f"- {evaluation.hypothesis_title} "
				f"[{evaluation.evidence_status.value}] "
				f"id={evaluation.hypothesis_id}"
			)
			print(
				"  completed_experiments="
				f"{evaluation.completed_experiment_count}, "
				f"trade_count={evaluation.total_trade_count}"
			)
			print(
				"  average_return="
				f"{_format_percent(evaluation.average_return)}, "
				f"win_rate={_format_percent(evaluation.win_rate)}, "
				f"best_return={_format_percent(evaluation.best_return)}, "
				f"worst_return={_format_percent(evaluation.worst_return)}"
			)
	else:
		print()
		print("No hypotheses to evaluate.")

	return evaluations


def run_manual_hypothesis_reviews(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	hypothesis_review_service=None,
):
	"""Run one-symbol hypothesis review generation on demand."""

	storage = storage or Storage()
	hypothesis_review_service = hypothesis_review_service or HypothesisReviewService(
		storage=storage
	)

	reviews = hypothesis_review_service.generate_for_symbol(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Reviews: {symbol}")
	print("=" * 50)
	print()
	print(f"Hypothesis Reviews Generated : {len(reviews)}")

	if reviews:
		print()
		print("Hypothesis Reviews")
		print("------------------")

		for review in reviews:
			print(
				f"- {review.hypothesis_id} "
				f"recommendation={review.recommendation.value} "
				f"confidence={review.confidence:.2f} "
				f"id={review.review_id}"
			)
			print(f"  rationale: {review.rationale}")
	else:
		print()
		print("No hypothesis reviews generated.")

	return reviews


def run_manual_hypothesis_lifecycle(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic hypothesis lifecycle recommendation policy for one symbol."""

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	load_hypothesis_reviews = getattr(storage, "load_hypothesis_reviews", None)
	hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Lifecycle: {symbol}")
	print("=" * 50)
	print()
	print("Recommendations only; no hypothesis state is changed.")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Lifecycle Recommendations : {len(recommendations)}")

	if recommendations:
		print()
		print("Hypothesis Lifecycle Recommendations")
		print("----------------------------------")

		for recommendation in recommendations:
			print(
				f"- {recommendation.hypothesis_title} "
				f"[{recommendation.current_status.value}] "
				f"id={recommendation.hypothesis_id} "
				f"action={recommendation.action.value}"
			)
			print(
				"  evidence="
				f"{recommendation.evidence_status.value}, "
				f"completed_experiments={recommendation.completed_experiment_count}, "
				f"trade_count={recommendation.total_trade_count}, "
				f"zero_trade_completed={recommendation.zero_trade_completed_experiment_count}"
			)

			if recommendation.review_recommendation is not None:
				print(
					"  latest_review="
					f"{recommendation.review_recommendation.value}, "
					f"confidence={recommendation.review_confidence:.2f}, "
					f"id={recommendation.review_id}"
				)

			print(f"  rationale: {recommendation.rationale}")
	else:
		print()
		print("No hypotheses to evaluate.")

	return recommendations


def run_manual_hypothesis_revisions(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	hypothesis_revision_service=None,
):
	"""Run one-symbol hypothesis revision proposal generation on demand."""

	storage = storage or Storage()
	hypothesis_revision_service = hypothesis_revision_service or HypothesisRevisionService(
		storage=storage
	)

	proposals = hypothesis_revision_service.generate_for_symbol(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Revisions: {symbol}")
	print("=" * 50)
	print()
	print("Proposals only; no hypotheses are mutated.")
	print(f"Hypothesis Revision Proposals Generated : {len(proposals)}")

	if proposals:
		print()
		print("Hypothesis Revision Proposals")
		print("-----------------------------")

		for proposal in proposals:
			print(
				f"- parent_id={proposal.parent_hypothesis_id} "
				f"proposal_type={proposal.proposal_type.value} "
				f"lifecycle_action={proposal.lifecycle_action.value} "
				f"confidence={proposal.confidence:.2f} "
				f"id={proposal.proposal_id}"
			)

			if proposal.source_review_id:
				print(f"  source_review_id: {proposal.source_review_id}")

			if proposal.proposed_title:
				print(f"  proposed_title: {proposal.proposed_title}")

			if proposal.proposed_description:
				print(f"  proposed_description: {proposal.proposed_description}")

			print(f"  rationale: {proposal.rationale}")
	else:
		print()
		print("No hypothesis revision proposals generated.")

	return proposals


def run_manual_hypothesis_revision_apply(
	symbol,
	proposal_id,
	apply_changes=False,
	storage=None,
	hypothesis_revision_application_service=None,
):
	"""Apply one revision proposal manually in dry-run or apply mode."""

	storage = storage or Storage()
	hypothesis_revision_application_service = (
		hypothesis_revision_application_service
		or HypothesisRevisionApplicationService(storage=storage)
	)

	application = hypothesis_revision_application_service.apply_proposal(
		symbol=symbol,
		proposal_id=proposal_id,
		apply_mode=apply_changes,
	)

	print()
	print("=" * 50)
	print(f"Manual Hypothesis Revision Apply: {symbol}")
	print("=" * 50)
	print()
	mode_text = "apply" if apply_changes else "dry-run"
	print(f"Mode : {mode_text}")
	print(f"Proposal ID : {proposal_id}")
	print(f"Application Status : {application.status.value}")
	print(f"Application ID : {application.application_id}")
	print(f"Parent Hypothesis ID : {application.parent_hypothesis_id}")

	if application.child_hypothesis_id:
		print(f"Child Hypothesis ID : {application.child_hypothesis_id}")

	if application.message:
		print(f"Message : {application.message}")

	print("Hypotheses are append-only; no historical records were mutated.")

	return application


def run_manual_promotion_candidates(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic read-only promotion candidate evaluation for one symbol."""

	def _format_percent(value):
		if value is None:
			return "n/a"

		return f"{value * 100:.2f}%"

	def _format_review_action(value):
		if value is None:
			return "none"

		return value.value

	def _format_yes_no(value):
		return "yes" if value else "no"

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	observations = storage.load_observations(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	hypothesis_reviews = storage.load_hypothesis_reviews(symbol)
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	freshness_items = build_research_freshness(
		hypotheses=hypotheses,
		observations=observations,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		hypothesis_reviews=hypothesis_reviews,
		revision_proposals=revision_proposals,
		lifecycle_recommendations=lifecycle_recommendations,
	)
	evaluations = evaluate_promotion_candidates(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		freshness_items=freshness_items,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)

	candidate_count = sum(
		1
		for evaluation in evaluations
		if evaluation.decision == PromotionCandidateDecision.CANDIDATE
	)

	print()
	print("=" * 50)
	print(f"Manual Promotion Candidates: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Candidates Evaluated : {len(evaluations)}")
	print(f"Promotion Candidates : {candidate_count}")

	print()
	print("Promotion Evaluation")
	print("--------------------")
	for evaluation in evaluations:
		print(f"- {evaluation.hypothesis_id} decision={evaluation.decision.value}")
		print(f"  evidence={evaluation.evidence_status.value}")
		print(f"  completed_experiments={evaluation.completed_experiments}")
		print(f"  trade_count={evaluation.trade_count}")
		print(f"  average_return={_format_percent(evaluation.average_return)}")
		print(f"  win_rate={_format_percent(evaluation.win_rate)}")
		print(f"  latest_review_action={_format_review_action(evaluation.latest_review_action)}")
		if evaluation.failed_checks:
			print(f"  failed_checks={', '.join(evaluation.failed_checks)}")
		print(f"  rationale: {evaluation.rationale}")

	not_candidate_count = len(evaluations) - candidate_count
	print()
	print("Promotion Summary")
	print("-----------------")
	print(f"- candidate : {candidate_count}")
	print(f"- not_candidate : {not_candidate_count}")

	print()
	print("Suggested Next Commands")
	print("-----------------------")
	print("No automatic promotion action is available. Promotion candidates require explicit human review.")

	print()
	print("Candidate Detail")
	print("----------------")
	candidate_evaluations = [
		evaluation
		for evaluation in evaluations
		if evaluation.decision == PromotionCandidateDecision.CANDIDATE
	]
	if candidate_evaluations:
		for evaluation in candidate_evaluations:
			print(f"- {evaluation.hypothesis_id}")
			print(
				"  evidence_strength: "
				f"completed_experiments={evaluation.completed_experiments}, "
				f"trade_count={evaluation.trade_count}, "
				f"average_return={_format_percent(evaluation.average_return)}, "
				f"win_rate={_format_percent(evaluation.win_rate)}, "
				f"best_return={_format_percent(evaluation.best_return)}, "
				f"worst_return={_format_percent(evaluation.worst_return)}"
			)
			print(
				"  review_state: "
				f"action={_format_review_action(evaluation.latest_review_action)}, "
				f"confidence={'n/a' if evaluation.latest_review_confidence is None else f'{evaluation.latest_review_confidence:.2f}'}, "
				f"current={_format_yes_no(evaluation.review_current)}"
			)
			if evaluation.latest_review_rationale:
				print(f"  latest_review_summary: {evaluation.latest_review_rationale}")
			print(
				"  risk_flags="
				+ (", ".join(evaluation.risk_flags) if evaluation.risk_flags else "none")
			)
			print("  required_human_checks:")
			print("    - Confirm hypothesis still makes economic sense.")
			print("    - Inspect experiment assumptions and setup conditions.")
			print("    - Check whether returns are overlapping or regime-dependent.")
			print("    - Check downside risk and worst-return behavior.")
			print("    - Decide whether to create a trade-candidate proposal.")
			print("  reminder: Promotion candidate is not approval to trade.")
	else:
		print("No promotion candidates available for candidate detail review.")

	print()
	print("Promotion candidate evaluation complete. No records were modified.")

	return evaluations


def run_manual_trade_candidate_proposals(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic read-only trade candidate proposal readiness for one symbol."""

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	observations = storage.load_observations(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	hypothesis_reviews = storage.load_hypothesis_reviews(symbol)
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	freshness_items = build_research_freshness(
		hypotheses=hypotheses,
		observations=observations,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		hypothesis_reviews=hypothesis_reviews,
		revision_proposals=revision_proposals,
		lifecycle_recommendations=lifecycle_recommendations,
	)
	promotion_evaluations = evaluate_promotion_candidates(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		freshness_items=freshness_items,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	readiness_items = evaluate_trade_candidate_proposals(promotion_evaluations)

	research_candidate_count = sum(
		1
		for evaluation in promotion_evaluations
		if evaluation.decision == PromotionCandidateDecision.CANDIDATE
	)
	proposal_ready_count = sum(
		1
		for item in readiness_items
		if item.decision == TradeCandidateProposalDecision.PROPOSAL_READY
	)

	print()
	print("=" * 50)
	print(f"Manual Trade Candidate Proposals: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Hypotheses Loaded : {len(hypotheses)}")
	print(f"Research Candidates Loaded : {research_candidate_count}")
	print(f"Trade Candidate Proposals : {proposal_ready_count}")

	print()
	print("Trade Candidate Proposal Readiness")
	print("----------------------------------")
	for item in readiness_items:
		print(f"- {item.hypothesis_id} decision={item.decision.value}")
		print(f"  source_decision={item.source_decision.value}")
		if item.required_components:
			print(f"  required_components={', '.join(item.required_components)}")
		if item.missing_components:
			print(f"  missing_components={', '.join(item.missing_components)}")
		print(f"  rationale: {item.rationale}")

	print()
	print("Proposal Design Checklist")
	print("-------------------------")
	proposal_ready_items = [
		item for item in readiness_items if item.decision == TradeCandidateProposalDecision.PROPOSAL_READY
	]
	if proposal_ready_items:
		for item in proposal_ready_items:
			print(f"- {item.hypothesis_id}")
			print("  - define entry trigger")
			print("  - define exit trigger")
			print("  - define invalidation condition")
			print("  - define maximum holding period")
			print("  - define position sizing rule")
			print("  - define max loss per trade")
			print("  - define max portfolio exposure")
			print("  - define demo-only enforcement")
			print("  - define monitoring frequency")
			print("  - define evidence conditions that would pause the setup")
	else:
		print("No trade candidate proposals are ready for design review.")

	print()
	print("Trade candidate proposal is not approval to trade.")
	print("Promotion comes only after demo-trading parameters/risk gates are defined and passed.")

	return readiness_items


def run_manual_demo_trade_candidates(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Inspect append-only demo trade candidates for one symbol in read-only mode."""

	storage = storage or Storage()
	candidates = storage.load_demo_trade_candidates(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Candidates: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Candidates Loaded : {len(candidates)}")

	if candidates:
		print()
		print("Demo Trade Candidates")
		print("---------------------")
		for candidate in candidates:
			validation_status = "valid"
			try:
				validate_demo_trade_candidate(candidate)
			except ValueError:
				validation_status = "invalid"

			print(f"- candidate_id={candidate.trade_candidate_id}")
			print(f"  source_hypothesis_id={candidate.source_hypothesis_id}")
			print(f"  status={candidate.status.value}")
			print(f"  demo_only={candidate.demo_only}")
			print(f"  validation={validation_status}")
	else:
		print()
		print("No demo trade candidates found.")

	return candidates


def run_manual_demo_trade_candidate_generation(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	demo_trade_candidate_service=None,
):
	"""Generate append-only AI demo trade candidates for qualified research candidates."""

	storage = storage or Storage()
	demo_trade_candidate_service = demo_trade_candidate_service or DemoTradeCandidateService(
		storage=storage,
	)
	result = demo_trade_candidate_service.generate_for_symbol(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Candidate Generation: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : yes")
	print("AI Calls Allowed : yes")
	print(f"Research Candidates Loaded : {result.research_candidates_loaded}")
	print(f"Generation Candidates : {result.generation_candidates}")
	print(f"Generated : {len(result.generated_candidates)}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Failed Validation : {result.failed_validation}")

	print()
	print("Generated Demo Trade Candidates")
	print("-------------------------------")
	if result.generated_candidates:
		for candidate in result.generated_candidates:
			print(f"- candidate_id={candidate.trade_candidate_id}")
			print(f"  source_hypothesis_id={candidate.source_hypothesis_id}")
			print(f"  status={candidate.status.value}")
			print("  validation=valid")
	else:
		print("No demo trade candidates generated.")

	return result


def run_manual_demo_trade_gate(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Run deterministic read-only gate evaluation for proposed demo trade candidates."""

	storage = storage or Storage()
	hypotheses = storage.load_hypotheses(symbol)
	observations = storage.load_observations(symbol)
	experiment_requests = storage.load_experiment_requests(symbol)
	experiment_results = storage.load_experiment_results(symbol)
	hypothesis_reviews = storage.load_hypothesis_reviews(symbol)
	revision_proposals = storage.load_hypothesis_revision_proposals(symbol)
	candidates = storage.load_demo_trade_candidates(symbol=symbol)

	evidence_summaries = evaluate_hypothesis_evidence(
		hypotheses=hypotheses,
		experiment_results=experiment_results,
		experiment_requests=experiment_requests,
	)
	latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
	lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	freshness_items = build_research_freshness(
		hypotheses=hypotheses,
		observations=observations,
		experiment_requests=experiment_requests,
		experiment_results=experiment_results,
		hypothesis_reviews=hypothesis_reviews,
		revision_proposals=revision_proposals,
		lifecycle_recommendations=lifecycle_recommendations,
	)
	promotion_evaluations = evaluate_promotion_candidates(
		hypotheses=hypotheses,
		evidence_summaries=evidence_summaries,
		freshness_items=freshness_items,
		latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
	)
	gate_evaluations = evaluate_demo_trade_gate(candidates, promotion_evaluations)

	gate_passed = sum(
		1
		for evaluation in gate_evaluations
		if evaluation.decision == DemoTradeGateDecision.GATE_PASS
	)
	gate_failed = sum(
		1
		for evaluation in gate_evaluations
		if evaluation.decision == DemoTradeGateDecision.GATE_FAIL
	)
	not_evaluated = sum(
		1
		for evaluation in gate_evaluations
		if evaluation.decision == DemoTradeGateDecision.NOT_EVALUATED
	)
	gate_evaluated = gate_passed + gate_failed

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Gate: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Candidates Loaded : {len(candidates)}")
	print(f"Gate Evaluated : {gate_evaluated}")
	print(f"Gate Passed : {gate_passed}")
	print(f"Gate Failed : {gate_failed}")
	print(f"Not Evaluated : {not_evaluated}")

	print()
	print("Demo Trade Gate Results")
	print("-----------------------")
	if gate_evaluations:
		for evaluation in gate_evaluations:
			print(f"- candidate_id={evaluation.trade_candidate_id}")
			print(f"  source_hypothesis_id={evaluation.source_hypothesis_id}")
			print(f"  status={evaluation.status.value}")
			print(f"  decision={evaluation.decision.value}")
			print(
				"  failed_checks="
				+ (", ".join(evaluation.failed_checks) if evaluation.failed_checks else "none")
			)
			print(
				"  risk_flags="
				+ (", ".join(evaluation.risk_flags) if evaluation.risk_flags else "none")
			)
			print(f"  rationale: {evaluation.rationale}")
	else:
		print("No demo trade candidates found.")

	print()
	print("Suggested Next Commands")
	print("-----------------------")
	print("Gate is read-only in this slice. No automatic demo queue action is available yet.")

	return gate_evaluations


def run_manual_demo_trade_gate_apply(
	symbol=DEFAULT_SYMBOL,
	apply_changes=False,
	storage=None,
	demo_trade_gate_apply_service=None,
):
	"""Preview or apply append-only demo trade gate outcomes for one symbol."""

	storage = storage or Storage()
	demo_trade_gate_apply_service = demo_trade_gate_apply_service or DemoTradeGateApplyService(
		storage=storage,
	)
	result = demo_trade_gate_apply_service.apply_for_symbol(
		symbol=symbol,
		apply_mode=apply_changes,
	)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Gate Apply: {symbol}")
	print("=" * 50)
	print()
	print(f"Mode : {'apply' if apply_changes else 'dry-run'}")
	print(f"Records Modified : {'yes' if apply_changes else 'no'}")
	print("AI Calls Allowed : no")
	print(f"Candidates Loaded : {result.candidates_loaded}")
	print(f"Gate Evaluated : {result.gate_evaluated}")
	print(f"Would Pass : {result.would_pass}")
	print(f"Would Fail : {result.would_fail}")
	print(f"Applied Passed : {result.applied_passed}")
	print(f"Applied Failed : {result.applied_failed}")
	print(f"Skipped Existing : {result.skipped_existing}")

	print()
	print("Applied Gate Results")
	print("--------------------")
	if result.applied_results:
		for item in result.applied_results:
			print(f"- candidate_id={item.trade_candidate_id}")
			print(f"  source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  previous_status={item.previous_status.value}")
			print(f"  new_status={item.new_status.value}")
			print(f"  decision={item.decision.value}")
	else:
		print("No gate outcomes available to apply.")

	print()
	if apply_changes:
		print("Apply reminder:")
		print("Gate outcomes were recorded append-only. No orders were created.")
	else:
		print("Dry-run reminder:")
		print("Dry-run only. No records were modified.")

	return result


def run_manual_demo_trade_queue(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Inspect append-only demo trade queue items for one symbol in read-only mode."""

	storage = storage or Storage()
	queue_items = storage.load_demo_trade_queue_items(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Queue: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print(f"Queue Items Loaded : {len(queue_items)}")

	if queue_items:
		print()
		print("Demo Trade Queue")
		print("----------------")
		for item in queue_items:
			print(f"- queue_item_id={item.queue_item_id}")
			print(f"  demo_trade_candidate_id={item.demo_trade_candidate_id}")
			print(f"  source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  status={item.status.value}")
			print(f"  requested_action={item.requested_action}")
			print(f"  demo_only={item.demo_only}")
	else:
		print()
		print("No demo trade queue items found.")

	return queue_items


def run_manual_demo_trade_queue_add(
	symbol=DEFAULT_SYMBOL,
	apply_changes=False,
	storage=None,
	demo_trade_queue_add_service=None,
):
	"""Preview or append demo trade queue items for eligible gate-passed candidates."""

	storage = storage or Storage()
	demo_trade_queue_add_service = demo_trade_queue_add_service or DemoTradeQueueAddService(
		storage=storage,
	)
	result = demo_trade_queue_add_service.apply_for_symbol(
		symbol=symbol,
		apply_mode=apply_changes,
	)
	records_modified = result.queued > 0

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Queue Add: {symbol}")
	print("=" * 50)
	print()
	print(f"Mode : {'apply' if apply_changes else 'dry-run'}")
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print(f"Gate Passed Candidates Loaded : {result.gate_passed_candidates_loaded}")
	print(f"Would Queue : {result.would_queue}")
	print(f"Queued : {result.queued}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")

	print()
	print("Queue Results")
	print("-------------")
	if result.results:
		for item in result.results:
			print(f"- demo_trade_candidate_id={item.demo_trade_candidate_id}")
			print(f"  source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  action={item.action}")
			print(f"  queue_item_id={item.queue_item_id if item.queue_item_id is not None else 'none'}")
	else:
		print("No gate-passed demo trade candidates were eligible for queue review.")

	print()
	if apply_changes:
		print("Apply reminder:")
		if records_modified:
			print("Queue records were created append-only. No orders were submitted.")
		else:
			print("No new queue records were created. Existing queue items were left unchanged. No orders were submitted.")
	else:
		print("Dry-run reminder:")
		print("Dry-run only. No queue records were created.")

	return result


def run_manual_demo_order_intents(
	symbol=DEFAULT_SYMBOL,
	storage=None,
):
	"""Inspect append-only demo order intents for one symbol in read-only mode."""

	storage = storage or Storage()
	intents = storage.load_demo_order_intents(symbol=symbol)

	print()
	print("=" * 50)
	print(f"Manual Demo Order Intents: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print(f"Order Intents Loaded : {len(intents)}")

	if intents:
		print()
		print("Demo Order Intents")
		print("------------------")
		for intent in intents:
			print(f"- order_intent_id={intent.order_intent_id}")
			print(f"  queue_item_id={intent.queue_item_id}")
			print(f"  demo_trade_candidate_id={intent.demo_trade_candidate_id}")
			print(f"  source_hypothesis_id={intent.source_hypothesis_id}")
			print(f"  status={intent.status.value}")
			print(f"  side={intent.side}")
			print(f"  order_type={intent.order_type}")
			print(f"  time_in_force={intent.time_in_force}")
			print(f"  notional={intent.notional}")
			print(f"  demo_only={intent.demo_only}")
			print("  validation=valid")
	else:
		print()
		print("No demo order intents found.")

	return intents


def run_manual_demo_order_intent_add(
	symbol=DEFAULT_SYMBOL,
	apply_changes=False,
	storage=None,
	demo_order_intent_add_service=None,
):
	"""Preview or append demo order intents created from queued demo queue items."""

	storage = storage or Storage()
	demo_order_intent_add_service = demo_order_intent_add_service or DemoOrderIntentAddService(
		storage=storage,
	)
	result = demo_order_intent_add_service.apply_for_symbol(
		symbol=symbol,
		apply_mode=apply_changes,
	)
	records_modified = result.prepared > 0

	print()
	print("=" * 50)
	print(f"Manual Demo Order Intent Add: {symbol}")
	print("=" * 50)
	print()
	print(f"Mode : {'apply' if apply_changes else 'dry-run'}")
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print(f"Queued Items Loaded : {result.queued_items_loaded}")
	print(f"Would Prepare : {result.would_prepare}")
	print(f"Prepared : {result.prepared}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")
	print(f"Failed Validation : {result.failed_validation}")

	print()
	print("Order Intent Results")
	print("--------------------")
	if result.results:
		for item in result.results:
			print(f"- queue_item_id={item.queue_item_id}")
			print(f"  demo_trade_candidate_id={item.demo_trade_candidate_id}")
			print(f"  source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  action={item.action}")
			print(f"  order_intent_id={item.order_intent_id if item.order_intent_id is not None else 'none'}")
			print(f"  notional={item.notional if item.notional is not None else 'none'}")
	else:
		print("No queued items were eligible for demo order intent review.")

	print()
	if apply_changes:
		print("Apply reminder:")
		if records_modified:
			print("Order intent records were created append-only. No orders were submitted.")
		else:
			print("No new order intent records were created. Existing intents were left unchanged. No orders were submitted.")
	else:
		print("Dry-run reminder:")
		print("Dry-run only. No order intent records were created. No orders were submitted.")

	return result


def run_manual_demo_paper_order_submit(
	symbol=DEFAULT_SYMBOL,
	apply_changes=False,
	confirm_paper_submit=False,
	storage=None,
	demo_paper_order_submit_service=None,
):
	"""Preview or submit prepared demo order intents to the Alpaca paper endpoint."""

	storage = storage or Storage()
	demo_paper_order_submit_service = demo_paper_order_submit_service or DemoPaperOrderSubmitService(
		storage=storage,
	)
	result = demo_paper_order_submit_service.apply_for_symbol(
		symbol=symbol,
		apply_mode=apply_changes,
		confirm_paper_submit=confirm_paper_submit,
	)
	records_modified = result.submitted > 0

	print()
	print("=" * 50)
	print(f"Manual Demo Paper Order Submit: {symbol}")
	print("=" * 50)
	print()
	broker_calls_allowed = bool(apply_changes and confirm_paper_submit)
	order_placement_allowed = bool(apply_changes and confirm_paper_submit)

	print(f"Mode : {'apply' if apply_changes else 'dry-run'}")
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print(f"Broker Calls Allowed : {'yes' if broker_calls_allowed else 'no'}")
	print(f"Order Placement Allowed : {'yes' if order_placement_allowed else 'no'}")
	print(f"Order Intents Loaded : {result.intents_loaded}")
	print(f"Would Submit : {result.would_submit}")
	print(f"Submitted : {result.submitted}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")
	print(f"Refused Without Confirmation : {result.refused_without_confirmation}")

	print()
	print("Paper Order Submit Results")
	print("--------------------------")
	if result.results:
		for item in result.results:
			print(f"- order_intent_id={item.order_intent_id}")
			print(f"  queue_item_id={item.queue_item_id}")
			print(f"  demo_trade_candidate_id={item.demo_trade_candidate_id}")
			print(f"  symbol={item.symbol}")
			print(f"  source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  action={item.action}")
			print(f"  broker_order_id={item.broker_order_id if item.broker_order_id is not None else 'none'}")
			print(f"  status={item.status if item.status is not None else 'none'}")
			print(f"  notional={item.notional if item.notional is not None else 'none'}")
	else:
		print("No prepared demo order intents were eligible for paper submit review.")

	print()
	if apply_changes:
		print("Apply reminder:")
		if confirm_paper_submit:
			if records_modified:
				print("Broker order records were created append-only. No live orders were submitted.")
			else:
				print("No broker order records were created. Existing records were left unchanged. No live orders were submitted.")
		elif result.refused_without_confirmation > 0:
			print("Paper submission refused. --confirm-paper-submit is required before any broker order record is appended.")
		else:
			print("No broker order records were created. Existing records were left unchanged. No live orders were submitted.")
	else:
		print("Dry-run reminder:")
		print("Dry-run only. No broker order records were created. No live orders were submitted.")

	return result


def run_manual_demo_broker_readiness(storage=None):
	"""Inspect deterministic demo broker readiness without network or broker calls."""

	storage = storage or Storage()
	queue_items = storage.load_demo_trade_queue_items()
	demo_broker_settings = settings.get_demo_broker_settings()
	readiness = evaluate_demo_broker_readiness(
		broker=demo_broker_settings["broker"],
		broker_mode=demo_broker_settings["mode"],
		broker_base_url=demo_broker_settings["base_url"],
		broker_api_key=demo_broker_settings["api_key"],
		broker_api_secret=demo_broker_settings["secret_key"],
		queue_items=queue_items,
	)

	print()
	print("=" * 50)
	print("Manual Demo Broker Readiness")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Queue Items Loaded : {readiness.queue_items_loaded}")
	print(f"Active Queue Items : {readiness.active_queue_items}")
	print(f"Ready : {'yes' if readiness.ready else 'no'}")

	print()
	print("Demo Broker Checks")
	print("------------------")
	print(f"- broker={readiness.broker}")
	print(f"- broker_mode={readiness.broker_mode}")
	print(f"  base_url_present={readiness.base_url_present}")
	print(f"  api_key_present={readiness.api_key_present}")
	print(f"  api_secret_present={readiness.api_secret_present}")
	print(f"  demo_only_queue_safe={readiness.demo_only_queue_safe}")
	print(f"  active_queue_items={readiness.active_queue_items}")
	print(f"  rationale: {readiness.rationale}")

	print()
	print("Failed Checks")
	print("-------------")
	if readiness.failed_checks:
		for check in readiness.failed_checks:
			print(f"- {check}")
	else:
		print("None.")

	return readiness


def run_manual_demo_broker_account(account_check_fn=check_demo_broker_account):
	"""Check the Alpaca paper account endpoint in read-only mode."""

	demo_broker_settings = settings.get_demo_broker_settings()
	account_check = account_check_fn(
		broker=demo_broker_settings["broker"],
		mode=demo_broker_settings["mode"],
		base_url=demo_broker_settings["base_url"],
		api_key=demo_broker_settings["api_key"],
		secret_key=demo_broker_settings["secret_key"],
	)

	print()
	print("=" * 50)
	print("Manual Demo Broker Account")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : yes")
	print("Order Placement Allowed : no")
	print("Live Mode Allowed : no")

	print()
	print("Broker Account Check")
	print("--------------------")
	print(f"- broker={account_check.broker}")
	print(f"- mode={account_check.mode}")
	print(f"- endpoint={account_check.endpoint}")
	print(f"- account_reachable={'yes' if account_check.account_reachable else 'no'}")
	print(f"- account_status={account_check.account_status}")
	print(f"- trading_blocked={account_check.trading_blocked}")
	print(f"- account_number={account_check.account_number}")

	print()
	print("Result")
	print("------")
	print(f"status={account_check.status}")
	print(f"rationale: {account_check.rationale}")

	print()
	print("This command only checks the paper/demo account. No orders were submitted.")

	return account_check


def run_manual_demo_broker_order_status_sync(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	status_sync_fn=sync_demo_broker_order_statuses,
):
	"""Sync append-only broker order status snapshots for previously submitted demo orders."""

	storage = storage or Storage()
	result = status_sync_fn(symbol=symbol, storage=storage)
	records_modified = result.records_modified

	print()
	print("=" * 50)
	print(f"Manual Demo Broker Order Status Sync: {symbol}")
	print("=" * 50)
	print()
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : yes")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Broker Order Records Loaded : {result.records_loaded}")
	print(f"Status Synced : {result.status_synced}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")
	print(f"Failed Sync : {result.failed_sync}")

	print()
	print("Broker Order Status Results")
	print("---------------------------")
	if result.refused_reason is not None:
		print(f"Refused : {result.refused_reason}")
	elif result.results:
		for item in result.results:
			print(f"- broker_order_id={item.broker_order_id if item.broker_order_id else 'none'}")
			print(f"  order_intent_id={item.order_intent_id if item.order_intent_id else 'none'}")
			print(f"  symbol={item.symbol}")
			print(f"  action={item.action}")
			print(f"  status={item.status if item.status is not None else 'none'}")
			print(f"  filled_qty={item.filled_qty if item.filled_qty is not None else 'none'}")
			print(f"  filled_avg_price={item.filled_avg_price if item.filled_avg_price is not None else 'none'}")
	else:
		print("No broker order records were eligible for status sync.")

	print()
	print("Reminder:")
	print("Broker order statuses were synced append-only. No orders were submitted, cancelled, or modified.")

	return result


def run_manual_demo_position_snapshot(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	snapshot_sync_fn=sync_demo_position_snapshot,
):
	"""Snapshot the current Alpaca paper position for one symbol in read-only mode."""

	storage = storage or Storage()
	result = snapshot_sync_fn(symbol=symbol, storage=storage)
	records_modified = result.records_modified
	position_found = result.position_found

	print()
	print("=" * 50)
	print(f"Manual Demo Position Snapshot: {symbol}")
	print("=" * 50)
	print()
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : yes")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Position Found : {'yes' if position_found else 'no'}")
	print(f"Snapshots Loaded : {result.snapshots_loaded}")
	print(f"Snapshots Created : {result.snapshots_created}")
	print(f"Failed Snapshot : {result.failed_snapshot}")

	print()
	print("Position Snapshot")
	print("-----------------")
	if result.refused_reason is not None:
		print(f"Refused : {result.refused_reason}")
	elif result.snapshot is not None:
		snapshot = result.snapshot
		print(f"- position_snapshot_id={snapshot.position_snapshot_id}")
		print(f"  symbol={snapshot.symbol}")
		print(f"  status={snapshot.status}")
		print(f"  qty={snapshot.qty if snapshot.qty is not None else 'none'}")
		print(f"  side={snapshot.side}")
		print(f"  market_value={snapshot.market_value if snapshot.market_value is not None else 'none'}")
		print(f"  cost_basis={snapshot.cost_basis if snapshot.cost_basis is not None else 'none'}")
		print(f"  avg_entry_price={snapshot.avg_entry_price if snapshot.avg_entry_price is not None else 'none'}")
		print(f"  current_price={snapshot.current_price if snapshot.current_price is not None else 'none'}")
		print(f"  unrealized_pl={snapshot.unrealized_pl if snapshot.unrealized_pl is not None else 'none'}")
		print(f"  unrealized_plpc={snapshot.unrealized_plpc if snapshot.unrealized_plpc is not None else 'none'}")
		print(f"  demo_only={snapshot.demo_only}")
	else:
		print("No position snapshot was created.")

	print()
	print("Reminder:")
	print("Position snapshot was appended locally. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_trade_performance_snapshot(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	performance_snapshot_fn=build_demo_trade_performance_snapshots,
):
	"""Build local demo trade performance snapshots from stored records only."""

	storage = storage or Storage()
	result = performance_snapshot_fn(symbol=symbol, storage=storage)
	records_modified = result.records_modified

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Performance Snapshot: {symbol}")
	print("=" * 50)
	print()
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Broker Orders Loaded : {result.broker_orders_loaded}")
	print(f"Filled Orders Evaluated : {result.filled_orders_evaluated}")
	print(f"Performance Snapshots Created : {result.performance_snapshots_created}")
	print(f"Skipped Not Filled : {result.skipped_not_filled}")
	print(f"Skipped Missing Position : {result.skipped_missing_position}")
	print(f"Failed Calculations : {result.failed_calculations}")

	print()
	print("Demo Trade Performance")
	print("----------------------")
	if result.snapshots:
		for snapshot in result.snapshots:
			print(f"- performance_snapshot_id={snapshot.performance_snapshot_id}")
			print(f"  order_intent_id={snapshot.order_intent_id}")
			print(f"  broker_order_id={snapshot.broker_order_id}")
			print(f"  source_hypothesis_id={snapshot.source_hypothesis_id}")
			print(f"  demo_trade_candidate_id={snapshot.demo_trade_candidate_id}")
			print(f"  status={snapshot.status}")
			print(f"  side={snapshot.side}")
			print(f"  filled_qty={snapshot.filled_qty if snapshot.filled_qty is not None else 'none'}")
			print(f"  filled_avg_price={snapshot.filled_avg_price if snapshot.filled_avg_price is not None else 'none'}")
			print(f"  current_price={snapshot.current_price if snapshot.current_price is not None else 'none'}")
			print(f"  entry_value={snapshot.entry_value if snapshot.entry_value is not None else 'none'}")
			print(f"  current_value={snapshot.current_value if snapshot.current_value is not None else 'none'}")
			print(f"  unrealized_pl={snapshot.unrealized_pl if snapshot.unrealized_pl is not None else 'none'}")
			print(f"  unrealized_plpc={snapshot.unrealized_plpc if snapshot.unrealized_plpc is not None else 'none'}")
			print(f"  demo_only={snapshot.demo_only}")
	else:
		print("No demo trade performance snapshots were created.")

	print()
	print("Summary")
	print("-------")
	print(f"total_entry_value={result.total_entry_value}")
	print(f"total_current_value={result.total_current_value}")
	print(f"total_unrealized_pl={result.total_unrealized_pl}")
	print(f"total_unrealized_plpc={result.total_unrealized_plpc}")

	print()
	print("Reminder:")
	print("Demo trade performance snapshots were appended locally. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_trade_performance_dashboard(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	dashboard_fn=build_demo_trade_performance_dashboard,
):
	"""Print a read-only demo trade performance dashboard from stored records only."""

	storage = storage or Storage()
	result = dashboard_fn(symbol=symbol, storage=storage)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Performance Dashboard: {symbol}")
	print("=" * 50)
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Performance Snapshots Loaded : {result.performance_snapshots_loaded}")
	print(f"Latest Trades Displayed : {result.latest_trades_displayed}")
	print(f"Hypotheses Displayed : {result.hypotheses_displayed}")

	print()
	print("Current Position Summary")
	print("------------------------")
	position_snapshot = result.position_snapshot
	if position_snapshot is not None:
		print(f"symbol={symbol}")
		print(f"position_snapshot_id={position_snapshot.position_snapshot_id}")
		print(f"qty={position_snapshot.qty if position_snapshot.qty is not None else 'none'}")
		print(f"market_value={position_snapshot.market_value if position_snapshot.market_value is not None else 'none'}")
		print(f"cost_basis={position_snapshot.cost_basis if position_snapshot.cost_basis is not None else 'none'}")
		print(f"unrealized_pl={position_snapshot.unrealized_pl if position_snapshot.unrealized_pl is not None else 'none'}")
		print(f"unrealized_plpc={position_snapshot.unrealized_plpc if position_snapshot.unrealized_plpc is not None else 'none'}")
	else:
		print(f"symbol={symbol}")
		print("No position snapshot is available locally.")

	print()
	print("Demo Trade Dashboard")
	print("--------------------")
	if result.trades:
		for trade in result.trades:
			print(f"- source_hypothesis_id={trade.source_hypothesis_id if trade.source_hypothesis_id else 'none'}")
			print(f"  demo_trade_candidate_id={trade.demo_trade_candidate_id if trade.demo_trade_candidate_id else 'none'}")
			print(f"  order_intent_id={trade.order_intent_id if trade.order_intent_id else 'none'}")
			print(f"  broker_order_id={trade.broker_order_id if trade.broker_order_id else 'none'}")
			print(f"  status={trade.status}")
			print(f"  current_rating={trade.current_rating}")
			print(f"  side={trade.side}")
			print(f"  filled_qty={trade.filled_qty if trade.filled_qty is not None else 'none'}")
			print(f"  filled_avg_price={trade.filled_avg_price if trade.filled_avg_price is not None else 'none'}")
			print(f"  current_price={trade.current_price if trade.current_price is not None else 'none'}")
			print(f"  entry_value={trade.entry_value if trade.entry_value is not None else 'none'}")
			print(f"  current_value={trade.current_value if trade.current_value is not None else 'none'}")
			print(f"  unrealized_pl={trade.unrealized_pl if trade.unrealized_pl is not None else 'none'}")
			print(f"  unrealized_plpc={trade.unrealized_plpc if trade.unrealized_plpc is not None else 'none'}")
			print(f"  demo_only={trade.demo_only}")
	else:
		print("No demo trade performance snapshots are available locally.")

	print()
	print("Hypothesis Summary")
	print("------------------")
	if result.hypotheses:
		for summary in result.hypotheses:
			print(f"- source_hypothesis_id={summary.source_hypothesis_id if summary.source_hypothesis_id else 'none'}")
			print(f"  trades={summary.trades}")
			print(f"  total_entry_value={summary.total_entry_value}")
			print(f"  total_current_value={summary.total_current_value}")
			print(f"  total_unrealized_pl={summary.total_unrealized_pl}")
			print(f"  total_unrealized_plpc={summary.total_unrealized_plpc}")
			print(f"  current_rating={summary.current_rating}")
			print(f"  promotion_status={summary.promotion_status}")
			print(f"  note={summary.note}")
	else:
		print("No hypotheses have demo trade performance data locally.")

	print()
	print("Reminder:")
	print("Dashboard is read-only and uses local snapshots. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_trade_evaluation(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	evaluation_fn=build_demo_trade_evaluations,
):
	"""Append deterministic demo trade evaluations from stored records only."""

	storage = storage or Storage()
	result = evaluation_fn(symbol=symbol, storage=storage)

	print()
	print("=" * 50)
	print(f"Manual Demo Trade Evaluation: {symbol}")
	print("=" * 50)
	print()
	print(f"Records Modified : {'yes' if result.records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Performance Snapshots Loaded : {result.performance_snapshots_loaded}")
	print(f"Evaluations Created : {result.evaluations_created}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")
	print(f"Failed Evaluations : {result.failed_evaluations}")

	print()
	print("Demo Trade Evaluations")
	print("----------------------")
	if result.evaluations:
		for evaluation in result.evaluations:
			print(f"- demo_trade_evaluation_id={evaluation.demo_trade_evaluation_id}")
			print(f"  source_hypothesis_id={evaluation.source_hypothesis_id if evaluation.source_hypothesis_id else 'none'}")
			print(f"  demo_trade_candidate_id={evaluation.demo_trade_candidate_id if evaluation.demo_trade_candidate_id else 'none'}")
			print(f"  order_intent_id={evaluation.order_intent_id if evaluation.order_intent_id else 'none'}")
			print(f"  broker_order_id={evaluation.broker_order_id if evaluation.broker_order_id else 'none'}")
			print(f"  performance_snapshot_id={evaluation.performance_snapshot_id}")
			print(f"  trading_days_elapsed={evaluation.trading_days_elapsed}")
			print(f"  evaluation_window_complete={evaluation.evaluation_window_complete}")
			print(f"  current_rating={evaluation.current_rating}")
			print(f"  evaluation_status={evaluation.evaluation_status}")
			print(f"  recommended_action={evaluation.recommended_action}")
			print(f"  unrealized_pl={evaluation.unrealized_pl if evaluation.unrealized_pl is not None else 'none'}")
			print(f"  unrealized_plpc={evaluation.unrealized_plpc if evaluation.unrealized_plpc is not None else 'none'}")
			print(f"  risk_breached={evaluation.risk_breached}")
			print(f"  demo_only={evaluation.demo_only}")
	else:
		print("No new demo trade evaluations were created.")

	print()
	print("Summary")
	print("-------")
	for status in EVALUATION_STATUS_ORDER:
		print(f"{status}={result.status_counts.get(status, 0)}")

	print()
	print("Reminder:")
	if result.evaluations_created > 0:
		print("Demo trade evaluations were appended locally. This is not promotion and not an exit order. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")
	else:
		print("No new demo trade evaluations were created. Existing evaluations were left unchanged. This is not promotion and not an exit order. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_hypothesis_performance_summary(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	summary_fn=build_demo_hypothesis_performance_summaries,
):
	"""Append deterministic per-hypothesis demo evidence summaries from stored evaluations only."""

	storage = storage or Storage()
	result = summary_fn(symbol=symbol, storage=storage)

	print()
	print("=" * 50)
	print(f"Manual Demo Hypothesis Performance Summary: {symbol}")
	print("=" * 50)
	print()
	print(f"Records Modified : {'yes' if result.records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Trade Evaluations Loaded : {result.trade_evaluations_loaded}")
	print(f"Hypotheses Summarized : {result.hypotheses_summarized}")
	print(f"Summaries Created : {result.summaries_created}")
	print(f"Skipped Existing : {result.skipped_existing}")
	print(f"Skipped Ineligible : {result.skipped_ineligible}")
	print(f"Failed Summaries : {result.failed_summaries}")

	print()
	print("Demo Hypothesis Performance Summary")
	print("-----------------------------------")
	if result.summaries:
		for summary in result.summaries:
			print(f"- demo_hypothesis_summary_id={summary.demo_hypothesis_summary_id}")
			print(f"  source_hypothesis_id={summary.source_hypothesis_id}")
			print(f"  trades_evaluated={summary.trades_evaluated}")
			print(f"  unique_demo_trade_candidates={summary.unique_demo_trade_candidates}")
			print(f"  needs_more_time_count={summary.needs_more_time_count}")
			print(f"  successful_window_count={summary.successful_window_count}")
			print(f"  flat_window_count={summary.flat_window_count}")
			print(f"  weak_window_count={summary.weak_window_count}")
			print(f"  risk_breach_count={summary.risk_breach_count}")
			print(f"  evaluation_window_complete_count={summary.evaluation_window_complete_count}")
			print(f"  total_entry_value={summary.total_entry_value}")
			print(f"  total_current_value={summary.total_current_value}")
			print(f"  total_unrealized_pl={summary.total_unrealized_pl}")
			print(f"  total_unrealized_plpc={summary.total_unrealized_plpc}")
			print(f"  average_unrealized_plpc={summary.average_unrealized_plpc}")
			print(f"  best_unrealized_plpc={summary.best_unrealized_plpc if summary.best_unrealized_plpc is not None else 'none'}")
			print(f"  worst_unrealized_plpc={summary.worst_unrealized_plpc if summary.worst_unrealized_plpc is not None else 'none'}")
			print(f"  risk_breach_rate={summary.risk_breach_rate}")
			print(f"  completion_rate={summary.completion_rate}")
			print(f"  current_summary_rating={summary.current_summary_rating}")
			print(f"  promotion_readiness={summary.promotion_readiness}")
			print(f"  note={summary.note}")
			print(f"  demo_only={summary.demo_only}")
	else:
		print("No new demo hypothesis performance summaries were created.")

	print()
	print("Summary")
	print("-------")
	print(f"hypotheses_summarized={result.hypotheses_summarized}")
	for rating in SUMMARY_RATING_ORDER:
		print(f"{rating}={result.rating_counts.get(rating, 0)}")

	print()
	print("Reminder:")
	if result.summaries_created > 0:
		print("Demo hypothesis performance summaries were appended locally. This is not promotion and not an exit order. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")
	else:
		print("No new demo hypothesis performance summaries were created. Existing summaries were left unchanged. This is not promotion and not an exit order. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_promotion_board(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	board_fn=build_demo_promotion_board,
):
	"""Show deterministic read-only recommendations from latest local demo summaries."""

	storage = storage or Storage()
	result = board_fn(symbol=symbol, storage=storage)

	print()
	print(f"Manual Demo Promotion Board: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Hypothesis Summaries Loaded : {result.hypothesis_summaries_loaded}")
	print(f"Board Items Displayed : {result.board_items_displayed}")
	print("Promotion Actions Taken : 0")

	print()
	print("Demo Promotion Board")
	print("--------------------")
	if result.board_items:
		for item in result.board_items:
			print(f"- source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  latest_summary_id={item.latest_summary_id}")
			print(f"  trades_evaluated={item.trades_evaluated}")
			print(f"  evaluation_window_complete_count={item.evaluation_window_complete_count}")
			print(f"  current_summary_rating={item.current_summary_rating}")
			print(f"  promotion_readiness={item.promotion_readiness}")
			print(f"  board_recommendation={item.board_recommendation}")
			print(f"  board_reason={','.join(item.board_reason)}")
			print(f"  total_unrealized_pl={item.total_unrealized_pl if item.total_unrealized_pl is not None else 'none'}")
			print(f"  total_unrealized_plpc={item.total_unrealized_plpc if item.total_unrealized_plpc is not None else 'none'}")
			print(f"  risk_breach_rate={item.risk_breach_rate if item.risk_breach_rate is not None else 'none'}")
			print(f"  completion_rate={item.completion_rate if item.completion_rate is not None else 'none'}")
			print(f"  action={item.action}")
			print(f"  note={item.note}")
	else:
		print("No demo hypothesis summaries are available locally.")

	print()
	print("Summary")
	print("-------")
	for recommendation in BOARD_RECOMMENDATION_ORDER:
		print(f"{recommendation}={result.recommendation_counts.get(recommendation, 0)}")

	print()
	print("Reminder:")
	print("Demo promotion board is read-only. No promotion was performed. No broker calls were made. No orders were submitted, cancelled, replaced, or closed.")

	return result


def run_manual_demo_current_opportunity_rating(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	rating_fn=build_demo_current_opportunity_ratings,
):
	"""Show deterministic current opportunity ratings from local demo snapshots only."""

	storage = storage or Storage()
	result = rating_fn(symbol=symbol, storage=storage)

	print()
	print(f"Manual Demo Current Opportunity Rating: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print(f"Ratings Displayed : {result.ratings_displayed}")

	print()
	print("Current Opportunity Ratings")
	print("---------------------------")
	if result.ratings:
		for rating in result.ratings:
			print(f"- source_hypothesis_id={rating.source_hypothesis_id}")
			print(f"  demo_trade_candidate_id={rating.demo_trade_candidate_id}")
			print(f"  order_intent_id={rating.order_intent_id}")
			print(f"  broker_order_id={rating.broker_order_id}")
			print(f"  latest_current_price={rating.latest_current_price if rating.latest_current_price is not None else 'none'}")
			print(f"  entry_price={rating.entry_price if rating.entry_price is not None else 'none'}")
			print(f"  entry_performance_rating={rating.entry_performance_rating}")
			print(f"  entry_unrealized_plpc={rating.entry_unrealized_plpc if rating.entry_unrealized_plpc is not None else 'none'}")
			print(f"  board_recommendation={rating.board_recommendation}")
			print(f"  hypothesis_summary_rating={rating.hypothesis_summary_rating}")
			print(f"  current_opportunity_rating={rating.current_opportunity_rating}")
			print(f"  opportunity_reason={rating.opportunity_reason}")
			print(f"  action={rating.action}")
			print(f"  note={rating.note}")
	else:
		print("No local demo trade performance snapshots are available.")

	print()
	print("Summary")
	print("-------")
	for rating_name in OPPORTUNITY_RATING_ORDER:
		print(f"{rating_name}={result.rating_counts.get(rating_name, 0)}")

	print()
	print("Reminder:")
	print("Current opportunity rating is read-only and uses local snapshots. No market data, broker, AI, order, close, or promotion actions were performed.")

	return result


def run_manual_demo_status_dashboard(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	dashboard_fn=build_demo_status_dashboard,
):
	"""Show the latest local demo state without writes, calls, or actions."""

	storage = storage or Storage()
	result = dashboard_fn(symbol=symbol, storage=storage)

	print()
	print(f"Manual Demo Status Dashboard: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")

	print()
	print("Position")
	print("--------")
	position = result.position_snapshot
	print(f"symbol={symbol}")
	if position is None:
		print("qty=none")
		print("market_value=none")
		print("cost_basis=none")
		print("unrealized_pl=none")
		print("unrealized_plpc=none")
	else:
		for field in ("qty", "market_value", "cost_basis", "unrealized_pl", "unrealized_plpc"):
			value = getattr(position, field, None)
			print(f"{field}={value if value is not None else 'none'}")

	print()
	print("Demo Trade Status")
	print("-----------------")
	if result.trades:
		for trade in result.trades:
			print(f"- source_hypothesis_id={trade.source_hypothesis_id}")
			print(f"  demo_trade_candidate_id={trade.demo_trade_candidate_id}")
			print(f"  order_intent_id={trade.order_intent_id}")
			print(f"  broker_order_id={trade.broker_order_id}")
			print(f"  entry_price={trade.entry_price if trade.entry_price is not None else 'none'}")
			print(f"  current_price={trade.current_price if trade.current_price is not None else 'none'}")
			print(f"  entry_performance_rating={trade.entry_performance_rating}")
			print(f"  entry_unrealized_plpc={trade.entry_unrealized_plpc if trade.entry_unrealized_plpc is not None else 'none'}")
			print(f"  trade_evaluation_status={trade.trade_evaluation_status}")
			print(f"  trade_recommended_action={trade.trade_recommended_action}")
			print(f"  hypothesis_summary_rating={trade.hypothesis_summary_rating}")
			print(f"  board_recommendation={trade.board_recommendation}")
			print(f"  current_opportunity_rating={trade.current_opportunity_rating}")
			print(f"  current_opportunity_action={trade.current_opportunity_action}")
			print(f"  exit_readiness={trade.exit_readiness}")
			print(f"  exit_reason={trade.exit_reason}")
			print(f"  exit_action={trade.exit_action}")
			print(f"  trading_days_elapsed={trade.trading_days_elapsed if trade.trading_days_elapsed is not None else 'none'}")
			print(f"  evaluation_window_trading_days={trade.evaluation_window_trading_days if trade.evaluation_window_trading_days is not None else 'none'}")
			print(f"  evaluation_days_remaining={trade.evaluation_days_remaining if trade.evaluation_days_remaining is not None else 'none'}")
			print(f"  evaluation_window_complete={trade.evaluation_window_complete if trade.evaluation_window_complete is not None else 'none'}")
			print(f"  demo_only={trade.demo_only}")
	else:
		print("No local demo trade performance snapshots are available.")

	print()
	print("Hypothesis Board Summary")
	print("------------------------")
	if result.hypotheses:
		for hypothesis in result.hypotheses:
			print(f"- source_hypothesis_id={hypothesis.source_hypothesis_id}")
			print(f"  trades_evaluated={hypothesis.trades_evaluated}")
			print(f"  current_summary_rating={hypothesis.current_summary_rating}")
			print(f"  promotion_readiness={hypothesis.promotion_readiness}")
			print(f"  board_recommendation={hypothesis.board_recommendation}")
			print(f"  board_reason={','.join(hypothesis.board_reason)}")
			print(f"  current_opportunity_rating={hypothesis.current_opportunity_rating}")
			print(f"  action={hypothesis.action}")
	else:
		print("No local hypothesis performance summaries are available.")

	print()
	print("Overall Summary")
	print("---------------")
	print(f"open_demo_trades={result.open_demo_trades}")
	print(f"total_entry_value={result.total_entry_value}")
	print(f"total_current_value={result.total_current_value}")
	print(f"total_unrealized_pl={result.total_unrealized_pl}")
	print(f"total_unrealized_plpc={result.total_unrealized_plpc}")
	for name in (
		"not_ready",
		"monitor",
		"review_later",
		"blocked",
		"attractive_now",
		"current_no_new_entry",
		"exit_hold",
		"exit_needs_more_time",
		"exit_candidate",
		"risk_exit_candidate",
		"exit_unknown",
		"completed_evaluation_windows",
		"incomplete_evaluation_windows",
		"min_evaluation_days_remaining",
		"max_evaluation_days_remaining",
	):
		print(f"{name}={result.rating_counts.get(name, 0)}")

	print()
	print("Latest Daily AI Review")
	print("----------------------")
	latest_review = getattr(result, "latest_daily_ai_review", None)
	if latest_review is None:
		print("No stored daily AI review found.")
	else:
		print(f"latest_ai_review_id={latest_review.demo_daily_ai_review_id}")
		print(f"latest_ai_review_at={latest_review.reviewed_at.isoformat()}")
		print(f"ai_model={latest_review.ai_model}")
		print(f"overall_assessment={latest_review.overall_assessment}")
		print(f"deeper_ai_review_needed={'yes' if latest_review.deeper_ai_review_needed else 'no'}")
		print(f"latest_ai_reason={latest_review.reason}")
		print(f"confidence={latest_review.confidence}")
		print("note=Stored advisory AI review only. No AI call was made by this dashboard.")

	print()
	print("AI Review Summary")
	print("-----------------")
	print(f"latest_ai_review_available={'yes' if latest_review is not None else 'no'}")
	print(
		"deeper_ai_review_needed="
		+ (
			"yes" if latest_review is not None and latest_review.deeper_ai_review_needed
			else "no" if latest_review is not None
			else "unknown"
		)
	)

	print()
	print("Reminder:")
	print("Demo status dashboard is read-only and uses local snapshots. No market data, broker, AI, order, close, or promotion actions were performed.")

	return result


def run_manual_demo_exit_readiness(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	readiness_fn=build_demo_exit_readiness,
):
	"""Show deterministic exit readiness without creating exits or changing records."""

	storage = storage or Storage()
	result = readiness_fn(symbol=symbol, storage=storage)

	print()
	print(f"Manual Demo Exit Readiness: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Exit Orders Created : 0")
	print("Positions Closed : 0")

	print()
	print("Exit Readiness")
	print("--------------")
	if result.items:
		for item in result.items:
			print(f"- source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  demo_trade_candidate_id={item.demo_trade_candidate_id}")
			print(f"  order_intent_id={item.order_intent_id}")
			print(f"  broker_order_id={item.broker_order_id}")
			print(f"  entry_price={item.entry_price if item.entry_price is not None else 'none'}")
			print(f"  current_price={item.current_price if item.current_price is not None else 'none'}")
			print(f"  entry_unrealized_plpc={item.entry_unrealized_plpc if item.entry_unrealized_plpc is not None else 'none'}")
			print(f"  trade_evaluation_status={item.trade_evaluation_status}")
			print(f"  evaluation_window_complete={item.evaluation_window_complete if item.evaluation_window_complete is not None else 'none'}")
			print(f"  risk_breached={item.risk_breached}")
			print(f"  current_opportunity_rating={item.current_opportunity_rating}")
			print(f"  exit_readiness={item.exit_readiness}")
			print(f"  exit_reason={item.exit_reason}")
			print(f"  action={item.action}")
			print(f"  note={item.note}")
	else:
		print("No local demo trade performance snapshots are available.")

	print()
	print("Summary")
	print("-------")
	for label in EXIT_READINESS_ORDER:
		print(f"{label}={result.readiness_counts.get(label, 0)}")

	print()
	print("Reminder:")
	print("Demo exit readiness is read-only. No exit orders were created. No orders were submitted, cancelled, replaced, or closed. No broker calls were made.")

	return result


def run_manual_demo_ai_review_trigger(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	trigger_fn=build_demo_ai_review_trigger,
):
	"""Decide whether demo AI review is warranted without calling AI."""

	storage = storage or Storage()
	result = trigger_fn(symbol=symbol, storage=storage)

	print()
	print(f"Manual Demo AI Review Trigger: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("AI Calls Made : 0")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")

	print()
	print("AI Review Trigger")
	print("-----------------")
	print(f"symbol={result.symbol}")
	print(f"ai_review_needed={'yes' if result.ai_review_needed else 'no'}")
	print(f"primary_trigger={result.primary_trigger}")
	print(f"recommended_action={result.recommended_action}")
	print(f"reason={result.reason}")
	print(f"review_scope={result.review_scope}")
	print(f"credits_spend_recommended={'yes' if result.credits_spend_recommended else 'no'}")

	print()
	print("Trigger Details")
	print("---------------")
	print(f"open_demo_trades={result.open_demo_trades}")
	print(f"evaluations_loaded={result.evaluations_loaded}")
	print(f"completed_evaluation_windows={result.completed_evaluation_windows}")
	print(f"risk_breaches={result.risk_breaches}")
	print(f"exit_candidates={result.exit_candidates}")
	print(f"risk_exit_candidates={result.risk_exit_candidates}")
	print(f"promotion_review_candidates={result.promotion_review_candidates}")
	print(f"disagreement_candidates={result.disagreement_candidates}")

	print()
	print("Per Hypothesis")
	print("--------------")
	if result.items:
		for item in result.items:
			print(f"- source_hypothesis_id={item.source_hypothesis_id}")
			print(f"  trade_evaluation_status={item.trade_evaluation_status}")
			print(f"  evaluation_window_complete={item.evaluation_window_complete if item.evaluation_window_complete is not None else 'none'}")
			print(f"  board_recommendation={item.board_recommendation}")
			print(f"  current_opportunity_rating={item.current_opportunity_rating}")
			print(f"  exit_readiness={item.exit_readiness}")
			print(f"  ai_review_needed={'yes' if item.ai_review_needed else 'no'}")
			print(f"  trigger={item.trigger}")
			print(f"  reason={item.reason}")
	else:
		print("No local demo review data is available.")

	print()
	print("Reminder:")
	print("Demo AI review trigger is read-only and does not call AI. No credits were spent by this command. No broker, market data, order, close, or promotion actions were performed.")

	return result


def run_manual_demo_daily_ai_review(
	symbol=DEFAULT_SYMBOL,
	confirm_ai_call=False,
	storage=None,
	ai_client=None,
):
	"""Run one confirmation-gated advisory AI review over local demo state."""

	storage = storage or Storage()
	status_dashboard = build_demo_status_dashboard(symbol=symbol, storage=storage)
	exit_readiness = build_demo_exit_readiness(symbol=symbol, storage=storage)
	trigger = build_demo_ai_review_trigger(symbol=symbol, storage=storage)
	dashboard_context, exit_context, trigger_context = build_review_context(
		status_dashboard=status_dashboard,
		exit_readiness=exit_readiness,
		trigger=trigger,
	)
	dashboard_fingerprint = fingerprint_context(dashboard_context)
	trigger_fingerprint = fingerprint_context(trigger_context)
	existing_reviews = storage.load_demo_daily_ai_reviews(symbol=symbol)
	duplicate = confirm_ai_call and any(
		review.source_dashboard_fingerprint == dashboard_fingerprint
		and review.source_trigger_fingerprint == trigger_fingerprint
		for review in existing_reviews
	)

	review = None
	ai_calls_made = 0
	records_modified = False
	skipped_existing = 0
	error = None
	if duplicate:
		skipped_existing = 1
	elif confirm_ai_call:
		try:
			if ai_client is None:
				from ai.client import AIClient

				ai_client = AIClient()
			response = ai_client.demo_daily_ai_review(
				symbol=symbol,
				dashboard=json.dumps(dashboard_context, sort_keys=True, default=str),
				exit_readiness=json.dumps(exit_context, sort_keys=True, default=str),
				trigger=json.dumps(trigger_context, sort_keys=True, default=str),
			)
			ai_calls_made = 1
			payload = parse_demo_daily_ai_review(response)
			review = new_review_from_payload(
				symbol=symbol,
				dashboard_fingerprint=dashboard_fingerprint,
				trigger_fingerprint=trigger_fingerprint,
				ai_model=str(getattr(ai_client, "model", "unknown")),
				payload=payload,
			)
			records_modified = bool(storage.save_demo_daily_ai_review(review))
			if not records_modified:
				skipped_existing = 1
				review = None
		except Exception as exc:
			error = str(exc)
	else:
		error = "confirmation is required"

	print()
	print(f"Manual Demo Daily AI Review: {symbol}")
	print()
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print(f"AI Calls Allowed : {'yes' if confirm_ai_call and not duplicate else 'no'}")
	print(f"AI Calls Made : {ai_calls_made}")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")
	if not confirm_ai_call and not duplicate:
		print()
		print("AI review requires --confirm-ai-call.")
		print("No credits were spent.")
	if duplicate:
		print()
		print("Skipped Existing : 1")
	if error and (confirm_ai_call or duplicate):
		print()
		print(f"Review Error : {error}")

	print()
	print("Daily AI Review")
	print("---------------")
	if review is not None:
		print(f"overall_assessment={review.overall_assessment}")
		print(f"what_changed_or_matters_today={review.what_changed_or_matters_today}")
		print(f"demo_trade_assessment={review.demo_trade_assessment}")
		print(f"exit_assessment={review.exit_assessment}")
		print(f"promotion_assessment={review.promotion_assessment}")
		print(f"current_opportunity_assessment={review.current_opportunity_assessment}")
		print(f"deeper_ai_review_needed={'yes' if review.deeper_ai_review_needed else 'no'}")
		print(f"reason={review.reason}")
		print(f"confidence={review.confidence}")
	else:
		print("No daily AI review was created.")

	print()
	print("Daily Reviews Created : " + ("1" if review is not None else "0"))
	print(f"Skipped Existing : {skipped_existing}")
	print()
	print("Reminder:")
	print("Daily AI review is advisory only. No broker, market data, order, close, live trading, or promotion actions were performed.")

	return {
		"symbol": symbol,
		"records_modified": records_modified,
		"ai_calls_made": ai_calls_made,
		"daily_reviews_created": 1 if review is not None else 0,
		"skipped_existing": skipped_existing,
		"review": review,
		"error": error,
	}


def run_manual_demo_daily_ai_reviews(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	limit=10,
):
	"""Display stored daily demo AI reviews without creating or calling anything."""

	storage = storage or Storage()
	reviews = list(storage.load_demo_daily_ai_reviews(symbol=symbol) or [])
	reviews.sort(
		key=lambda review: getattr(review, "reviewed_at", datetime.min.replace(tzinfo=timezone.utc)),
		reverse=True,
	)
	displayed_reviews = reviews[:limit]

	print()
	print(f"Manual Demo Daily AI Reviews: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("AI Calls Made : 0")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")
	print(f"Daily Reviews Loaded : {len(reviews)}")
	print(f"Daily Reviews Displayed : {len(displayed_reviews)}")

	print()
	print("Daily AI Review History")
	print("-----------------------")
	if displayed_reviews:
		for review in displayed_reviews:
			print(f"- review_id={review.demo_daily_ai_review_id}")
			print(f"  reviewed_at={review.reviewed_at.isoformat()}")
			print(f"  ai_model={review.ai_model}")
			print(f"  ai_review_type={review.ai_review_type}")
			print(f"  overall_assessment={review.overall_assessment}")
			print(f"  demo_trade_assessment={review.demo_trade_assessment}")
			print(f"  exit_assessment={review.exit_assessment}")
			print(f"  promotion_assessment={review.promotion_assessment}")
			print(f"  current_opportunity_assessment={review.current_opportunity_assessment}")
			print(f"  deeper_ai_review_needed={'yes' if review.deeper_ai_review_needed else 'no'}")
			print(f"  reason={review.reason}")
			print(f"  confidence={review.confidence}")
			print(f"  demo_only={review.demo_only}")
	else:
		print("No stored daily AI reviews are available.")

	latest_review = displayed_reviews[0] if displayed_reviews else None
	deeper_count = sum(bool(review.deeper_ai_review_needed) for review in reviews)
	print()
	print("Summary")
	print("-------")
	print(f"latest_review_at={latest_review.reviewed_at.isoformat() if latest_review else 'none'}")
	print(f"reviews_loaded={len(reviews)}")
	print(f"deeper_ai_review_needed_count={deeper_count}")
	print(f"latest_reason={latest_review.reason if latest_review else 'none'}")

	print()
	print("Reminder:")
	print("Daily AI review history is read-only. No AI, broker, market data, order, close, live trading, or promotion actions were performed.")

	return {
		"symbol": symbol,
		"reviews_loaded": len(reviews),
		"reviews_displayed": len(displayed_reviews),
		"reviews": tuple(displayed_reviews),
	}


def run_manual_demo_monitoring_cycle(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	status_sync_fn=sync_demo_broker_order_statuses,
	snapshot_sync_fn=sync_demo_position_snapshot,
	performance_snapshot_fn=build_demo_trade_performance_snapshots,
	dashboard_fn=build_demo_trade_performance_dashboard,
	evaluation_fn=build_demo_trade_evaluations,
	summary_fn=build_demo_hypothesis_performance_summaries,
	board_fn=build_demo_promotion_board,
):
	"""Run the existing safe demo monitoring and evaluation steps in order."""

	storage = storage or Storage()
	steps = []

	def run_step(name, function, **kwargs):
		try:
			result = function(symbol=symbol, storage=storage, **kwargs)
			explicit_failure = False
			for field in (
				"failed_sync",
				"failed_snapshot",
				"failed_calculations",
				"failed_evaluations",
				"failed_summaries",
			):
				failure_count = getattr(result, field, 0)
				if isinstance(failure_count, (int, float)) and failure_count > 0:
					explicit_failure = True
					break
			refused = getattr(result, "refused_reason", None)
			steps.append({
				"name": name,
				"status": "failed" if explicit_failure else "completed",
				"result": result,
				"error": refused,
			})
			return result
		except Exception as exc:
			steps.append({"name": name, "status": "failed", "result": None, "error": str(exc)})
			return None

	status_result = run_step("broker_order_status_sync", status_sync_fn)
	position_result = run_step("position_snapshot", snapshot_sync_fn)
	performance_result = run_step("trade_performance_snapshot", performance_snapshot_fn)
	dashboard_result = run_step("trade_performance_dashboard", dashboard_fn)
	evaluation_result = run_step("trade_evaluation", evaluation_fn)
	summary_result = run_step("hypothesis_performance_summary", summary_fn)
	board_result = run_step("promotion_board", board_fn)

	def value(result, name, default=0):
		return getattr(result, name, default) if result is not None else default

	records_modified = any(
		bool(value(step["result"], "records_modified", False))
		for step in steps
	)
	warnings = any(step["status"] == "failed" for step in steps)
	cycle_status = "completed_with_warnings" if warnings else "completed"

	print()
	print(f"Manual Demo Monitoring Cycle: {symbol}")
	print()
	print(f"Records Modified : {'yes' if records_modified else 'no'}")
	print("AI Calls Allowed : no")
	print("Broker Calls Allowed : yes")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")

	print()
	print("Steps")
	print("-----")
	for step in steps:
		step_result = step["result"]
		print(f"- {step['name']}: {step['status']}")
		print(f"  records_modified={'yes' if value(step_result, 'records_modified', False) else 'no'}")
		if step["name"] == "broker_order_status_sync":
			print(f"  synced={value(step_result, 'status_synced')}")
			print(f"  failed={value(step_result, 'failed_sync')}")
		elif step["name"] == "position_snapshot":
			print(f"  position_found={'yes' if value(step_result, 'position_found', False) else 'no'}")
			print(f"  snapshots_created={value(step_result, 'snapshots_created')}")
		elif step["name"] == "trade_performance_snapshot":
			print(f"  snapshots_created={value(step_result, 'performance_snapshots_created')}")
		elif step["name"] == "trade_performance_dashboard":
			print(f"  latest_trades_displayed={value(step_result, 'latest_trades_displayed')}")
		elif step["name"] == "trade_evaluation":
			print(f"  evaluations_created={value(step_result, 'evaluations_created')}")
			print(f"  skipped_existing={value(step_result, 'skipped_existing')}")
		elif step["name"] == "hypothesis_performance_summary":
			print(f"  summaries_created={value(step_result, 'summaries_created')}")
			print(f"  skipped_existing={value(step_result, 'skipped_existing')}")
		elif step["name"] == "promotion_board":
			print(f"  board_items_displayed={value(step_result, 'board_items_displayed')}")
			print("  promotion_actions_taken=0")
		if step["error"]:
			print(f"  error={step['error']}")

	print()
	print("Cycle Summary")
	print("-------------")
	print(f"broker_status_synced={value(status_result, 'status_synced')}")
	print(f"position_snapshots_created={value(position_result, 'snapshots_created')}")
	print(f"performance_snapshots_created={value(performance_result, 'performance_snapshots_created')}")
	print(f"evaluations_created={value(evaluation_result, 'evaluations_created')}")
	print(f"hypothesis_summaries_created={value(summary_result, 'summaries_created')}")
	print(f"board_items_displayed={value(board_result, 'board_items_displayed')}")
	print(f"cycle_status={cycle_status}")

	print()
	print("Reminder:")
	print("Demo monitoring cycle completed using safe read/snapshot/evaluation steps. No orders were submitted, cancelled, replaced, or closed. No promotion was performed.")

	return {
		"symbol": symbol,
		"records_modified": records_modified,
		"cycle_status": cycle_status,
		"steps": tuple(steps),
	}


def run_manual_demo_daily_operator(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	monitoring_cycle_fn=run_manual_demo_monitoring_cycle,
	status_dashboard_fn=run_manual_demo_status_dashboard,
	ai_review_requested=False,
	confirm_ai_call=False,
	daily_ai_review_fn=run_manual_demo_daily_ai_review,
):
	"""Run the safe monitoring cycle, then display the latest local demo status."""

	storage = storage or Storage()
	cycle_result = None
	cycle_error = None
	cycle_output = io.StringIO()
	with redirect_stdout(cycle_output):
		try:
			cycle_result = monitoring_cycle_fn(symbol=symbol, storage=storage)
		except Exception as exc:
			cycle_error = str(exc)

	dashboard_result = None
	dashboard_error = None
	dashboard_output = io.StringIO()
	with redirect_stdout(dashboard_output):
		try:
			dashboard_result = status_dashboard_fn(symbol=symbol, storage=storage)
		except Exception as exc:
			dashboard_error = str(exc)

	ai_review_result = None
	ai_review_error = None
	ai_review_output = io.StringIO()
	if ai_review_requested:
		with redirect_stdout(ai_review_output):
			try:
				ai_review_result = daily_ai_review_fn(
					symbol=symbol,
					storage=storage,
					confirm_ai_call=confirm_ai_call,
				)
			except Exception as exc:
				ai_review_error = str(exc)

	cycle_status = (
		cycle_result.get("cycle_status", "failed")
		if isinstance(cycle_result, dict)
		else "failed"
	)
	cycle_records_modified = bool(
		cycle_result.get("records_modified", False)
		if isinstance(cycle_result, dict)
		else False
	)
	if cycle_error:
		cycle_status = "failed"

	dashboard_displayed = dashboard_result is not None and dashboard_error is None
	operator_status = "completed"
	if cycle_status != "completed" or not dashboard_displayed:
		operator_status = "completed_with_warnings"
	if cycle_status == "failed" and not dashboard_displayed:
		operator_status = "failed"
	if ai_review_error or (
		isinstance(ai_review_result, dict) and ai_review_result.get("error")
	):
		operator_status = "completed_with_warnings"
	operator_records_modified = cycle_records_modified or bool(
		isinstance(ai_review_result, dict)
		and ai_review_result.get("records_modified", False)
	)

	print()
	print(f"Manual Demo Daily Operator: {symbol}")
	print()
	print(f"Records Modified : {'yes' if operator_records_modified else 'no'}")
	print(f"AI Calls Allowed : {'yes' if ai_review_requested and confirm_ai_call else 'no'}")
	print("Broker Calls Allowed : yes")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")

	print()
	print("Operator Steps")
	print("--------------")
	print(f"- demo_monitoring_cycle: {'failed' if cycle_error else 'completed'}")
	print(f"  cycle_status={cycle_status}")
	print(f"  records_modified={'yes' if cycle_records_modified else 'no'}")
	if cycle_error:
		print(f"  error={cycle_error}")

	open_demo_trades = 0
	current_no_new_entry = 0
	if dashboard_result is not None:
		open_demo_trades = getattr(dashboard_result, "open_demo_trades", 0)
		current_no_new_entry = getattr(
			dashboard_result,
			"rating_counts",
			{},
		).get("current_no_new_entry", 0)
	print(f"- demo_status_dashboard: {'completed' if dashboard_displayed else 'failed'}")
	print("  records_modified=no")
	print(f"  open_demo_trades={open_demo_trades}")
	print(f"  current_no_new_entry={current_no_new_entry}")
	if dashboard_error:
		print(f"  error={dashboard_error}")

	if dashboard_displayed:
		print()
		print(dashboard_output.getvalue(), end="")

	ai_calls_made = 0
	daily_reviews_created = 0
	skipped_existing = 0
	deeper_ai_review_needed = "no"
	ai_review_reason = "not_requested"
	if isinstance(ai_review_result, dict):
		ai_calls_made = ai_review_result.get("ai_calls_made", 0)
		daily_reviews_created = ai_review_result.get("daily_reviews_created", 0)
		skipped_existing = ai_review_result.get("skipped_existing", 0)
		review = ai_review_result.get("review")
		if review is not None:
			deeper_ai_review_needed = "yes" if review.deeper_ai_review_needed else "no"
			ai_review_reason = review.reason
		elif not confirm_ai_call:
			ai_review_reason = "confirmation_required"
		elif skipped_existing:
			ai_review_reason = "duplicate_latest_state"
	if ai_review_error:
		ai_review_reason = "ai_review_error"

	print()
	print("AI Review")
	print("---------")
	print(f"ai_review_requested={'yes' if ai_review_requested else 'no'}")
	print(f"ai_review_confirmed={'yes' if ai_review_requested and confirm_ai_call else 'no'}")
	print(
		"ai_review_completed="
		+ (
			"yes"
			if isinstance(ai_review_result, dict)
			and not ai_review_error
			and not ai_review_result.get("error")
			else "no"
		)
	)
	print(f"ai_calls_made={ai_calls_made}")
	print(f"daily_reviews_created={daily_reviews_created}")
	print(f"skipped_existing={skipped_existing}")
	print(f"deeper_ai_review_needed={deeper_ai_review_needed}")
	print(f"ai_review_reason={ai_review_reason}")
	if ai_review_error:
		print(f"error={ai_review_error}")
	if ai_review_requested and ai_review_output.getvalue():
		print()
		print(ai_review_output.getvalue(), end="")

	print()
	print("Operator Summary")
	print("----------------")
	print(f"operator_status={operator_status}")
	print(f"monitoring_cycle_status={cycle_status}")
	print(f"dashboard_displayed={'yes' if dashboard_displayed else 'no'}")
	print(f"ai_review_requested={'yes' if ai_review_requested else 'no'}")
	print(f"ai_calls_made={ai_calls_made}")
	print(f"daily_ai_reviews_created={daily_reviews_created}")
	print("orders_submitted=0")
	print("orders_cancelled=0")
	print("positions_closed=0")
	print("promotions_performed=0")

	print()
	print("Reminder:")
	print("Demo daily operator completed using safe monitoring and dashboard steps. No orders were submitted, cancelled, replaced, or closed. No promotion was performed. Live trading remains disabled.")

	return {
		"symbol": symbol,
		"records_modified": operator_records_modified,
		"operator_status": operator_status,
		"monitoring_cycle_status": cycle_status,
		"dashboard_displayed": dashboard_displayed,
		"ai_review_requested": ai_review_requested,
		"ai_review_confirmed": ai_review_requested and confirm_ai_call,
		"ai_calls_made": ai_calls_made,
		"daily_reviews_created": daily_reviews_created,
		"skipped_existing": skipped_existing,
		"cycle_result": cycle_result,
		"dashboard_result": dashboard_result,
	}


def run_manual_demo_operator_runbook(symbol=DEFAULT_SYMBOL):
	"""Print recommended demo operator commands without executing any command."""

	print()
	print(f"Manual Demo Operator Runbook: {symbol}")
	print()
	print("Records Modified : no")
	print("AI Calls Allowed : no")
	print("AI Calls Made : 0")
	print("Broker Calls Allowed : no")
	print("Market Data Calls Allowed : no")
	print("Order Placement Allowed : no")
	print("Order Cancellation Allowed : no")
	print("Position Close Allowed : no")
	print("Live Mode Allowed : no")
	print("Promotion Actions Taken : 0")

	print()
	print("Daily Commands")
	print("--------------")
	print("1. Safe daily monitoring, no AI:")
	print(f"   python -m research.runner demo-daily-operator {symbol}")
	print()
	print("2. Safe daily monitoring with advisory AI review:")
	print(f"   python -m research.runner demo-daily-operator {symbol} --ai-review --confirm-ai-call")
	print()
	print("3. View stored AI reviews without spending credits:")
	print(f"   python -m research.runner demo-daily-ai-reviews {symbol}")
	print()
	print("4. View status dashboard only:")
	print(f"   python -m research.runner demo-status-dashboard {symbol}")
	print()
	print("5. View exit readiness only:")
	print(f"   python -m research.runner demo-exit-readiness {symbol}")
	print()
	print("6. View AI review trigger only:")
	print(f"   python -m research.runner demo-ai-review-trigger {symbol}")

	print()
	print("Safety Notes")
	print("------------")
	print("- Daily operator may call the paper broker only for read-only status/position snapshots.")
	print("- Daily operator does not submit, cancel, replace, or close orders.")
	print("- AI review is advisory only.")
	print("- AI review requires --confirm-ai-call.")
	print("- Live trading remains disabled.")
	print("- Promotion is not performed by these commands.")
	print("- Runtime records under ai/memory/ are not committed.")

	print()
	print("Recommended Normal Use")
	print("----------------------")
	print("Most days:")
	print(f"python -m research.runner demo-daily-operator {symbol}")
	print()
	print("When you want one advisory AI review:")
	print(f"python -m research.runner demo-daily-operator {symbol} --ai-review --confirm-ai-call")

	print()
	print("Reminder:")
	print("Demo operator runbook is read-only. No AI, broker, market data, order, close, live trading, or promotion actions were performed.")

	return {"symbol": symbol, "records_modified": False}


def _build_arg_parser():
	"""Build command-line parser for manual research runners."""

	parser = argparse.ArgumentParser(
		prog="python -m research.runner",
		description="Manual one-symbol research runners.",
	)
	subparsers = parser.add_subparsers(dest="mode")

	hypotheses_parser = subparsers.add_parser(
		"hypotheses",
		help="Generate hypotheses for one symbol.",
	)
	hypotheses_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	experiment_requests_parser = subparsers.add_parser(
		"experiment-requests",
		help="Generate experiment requests for one symbol.",
	)
	experiment_requests_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	experiment_requests_parser.add_argument(
		"--planned-only",
		action="store_true",
		help="Limit experiment request generation to hypotheses selected by the research plan.",
	)

	experiment_execution_parser = subparsers.add_parser(
		"experiment-execution",
		help="Execute stored experiment requests for one symbol.",
	)
	experiment_execution_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	experiment_execution_parser.add_argument(
		"--period",
		help=(
			"Historical lookback period for backtest execution "
			f"(default: {settings.BACKTEST_PERIOD})."
		),
	)
	experiment_execution_parser.add_argument(
		"--interval",
		help=(
			"Historical sampling interval for backtest execution "
			f"(default: {settings.BACKTEST_INTERVAL})."
		),
	)

	hypothesis_evaluation_parser = subparsers.add_parser(
		"hypothesis-evaluation",
		help="Summarize completed experiment evidence for hypotheses.",
	)
	hypothesis_evaluation_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	hypothesis_reviews_parser = subparsers.add_parser(
		"hypothesis-reviews",
		help="Generate AI hypothesis review recommendations for one symbol.",
	)
	hypothesis_reviews_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	hypothesis_lifecycle_parser = subparsers.add_parser(
		"hypothesis-lifecycle",
		help="Recommend deterministic lifecycle actions for one symbol.",
	)
	hypothesis_lifecycle_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	hypothesis_revisions_parser = subparsers.add_parser(
		"hypothesis-revisions",
		help="Generate hypothesis revision proposals for one symbol.",
	)
	hypothesis_revisions_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	research_plan_parser = subparsers.add_parser(
		"research-plan",
		help="Build a deterministic research plan for one symbol.",
	)
	research_plan_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	research_state_parser = subparsers.add_parser(
		"research-state",
		help="Show deterministic read-only research state for one symbol.",
	)
	research_state_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	research_dashboard_parser = subparsers.add_parser(
		"research-dashboard",
		help="Show deterministic read-only research dashboard for configured watchlist symbols.",
	)
	research_dashboard_parser.add_argument(
		"symbols",
		nargs="*",
		help="Optional symbols to review; defaults to config.settings.WATCHLIST.",
	)

	research_freshness_parser = subparsers.add_parser(
		"research-freshness",
		help="Show deterministic read-only freshness analysis for one symbol.",
	)
	research_freshness_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	promotion_candidates_parser = subparsers.add_parser(
		"promotion-candidates",
		help="Show deterministic read-only promotion candidate evaluation for one symbol.",
	)
	promotion_candidates_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	trade_candidate_proposals_parser = subparsers.add_parser(
		"trade-candidate-proposals",
		help="Show deterministic read-only trade candidate proposal readiness for one symbol.",
	)
	trade_candidate_proposals_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_candidates_parser = subparsers.add_parser(
		"demo-trade-candidates",
		help="Inspect append-only demo trade candidates for one symbol in read-only mode.",
	)
	demo_trade_candidates_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_candidate_generation_parser = subparsers.add_parser(
		"demo-trade-candidate-generation",
		help="Generate append-only AI demo trade candidates for one symbol.",
	)
	demo_trade_candidate_generation_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_gate_parser = subparsers.add_parser(
		"demo-trade-gate",
		help="Evaluate deterministic read-only gate checks for proposed demo trade candidates.",
	)
	demo_trade_gate_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_gate_apply_parser = subparsers.add_parser(
		"demo-trade-gate-apply",
		help="Preview or append deterministic demo trade gate outcomes for one symbol.",
	)
	demo_trade_gate_apply_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_trade_gate_apply_mode_group = demo_trade_gate_apply_parser.add_mutually_exclusive_group()
	demo_trade_gate_apply_mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview deterministic gate outcomes without modifying records (default).",
	)
	demo_trade_gate_apply_mode_group.add_argument(
		"--apply",
		action="store_true",
		help="Append deterministic gate outcome records for proposed demo trade candidates.",
	)

	demo_trade_queue_parser = subparsers.add_parser(
		"demo-trade-queue",
		help="Inspect append-only demo trade queue items for one symbol in read-only mode.",
	)
	demo_trade_queue_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_queue_add_parser = subparsers.add_parser(
		"demo-trade-queue-add",
		help="Preview or append demo trade queue items for one symbol.",
	)
	demo_trade_queue_add_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_trade_queue_add_mode_group = demo_trade_queue_add_parser.add_mutually_exclusive_group()
	demo_trade_queue_add_mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview queue entries without modifying records (default).",
	)
	demo_trade_queue_add_mode_group.add_argument(
		"--apply",
		action="store_true",
		help="Append queue entries for eligible demo trade candidates.",
	)

	demo_order_intents_parser = subparsers.add_parser(
		"demo-order-intents",
		help="Inspect append-only demo order intents for one symbol in read-only mode.",
	)
	demo_order_intents_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_order_intent_add_parser = subparsers.add_parser(
		"demo-order-intent-add",
		help="Preview or append local demo order intents for one symbol.",
	)
	demo_order_intent_add_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_order_intent_add_mode_group = demo_order_intent_add_parser.add_mutually_exclusive_group()
	demo_order_intent_add_mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview demo order intents without modifying records (default).",
	)
	demo_order_intent_add_mode_group.add_argument(
		"--apply",
		action="store_true",
		help="Append prepared demo order intents for eligible queued items.",
	)

	demo_paper_order_submit_parser = subparsers.add_parser(
		"demo-paper-order-submit",
		help="Preview or submit prepared demo order intents to the paper broker with explicit confirmation.",
	)
	demo_paper_order_submit_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_paper_order_submit_mode_group = demo_paper_order_submit_parser.add_mutually_exclusive_group()
	demo_paper_order_submit_mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview paper submissions without modifying records (default).",
	)
	demo_paper_order_submit_mode_group.add_argument(
		"--apply",
		action="store_true",
		help="Attempt paper order submission for prepared demo order intents.",
	)
	demo_paper_order_submit_parser.add_argument(
		"--confirm-paper-submit",
		action="store_true",
		help="Require explicit confirmation before appending paper broker order records.",
	)

	demo_broker_readiness_parser = subparsers.add_parser(
		"demo-broker-readiness",
		help="Show deterministic read-only demo broker readiness.",
	)

	demo_broker_account_parser = subparsers.add_parser(
		"demo-broker-account",
		help="Check the Alpaca paper/demo account endpoint in read-only mode.",
	)
	demo_broker_order_status_sync_parser = subparsers.add_parser(
		"demo-broker-order-status-sync",
		help="Sync append-only status snapshots for previously submitted demo broker orders.",
	)
	demo_broker_order_status_sync_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_position_snapshot_parser = subparsers.add_parser(
		"demo-position-snapshot",
		help="Snapshot the current Alpaca paper position for one symbol in read-only mode.",
	)
	demo_position_snapshot_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_performance_snapshot_parser = subparsers.add_parser(
		"demo-trade-performance-snapshot",
		help="Build local append-only demo trade performance snapshots for one symbol.",
	)
	demo_trade_performance_snapshot_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_performance_dashboard_parser = subparsers.add_parser(
		"demo-trade-performance-dashboard",
		help="Show a read-only demo trade performance dashboard for one symbol.",
	)
	demo_trade_performance_dashboard_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_trade_evaluation_parser = subparsers.add_parser(
		"demo-trade-evaluation",
		help="Append deterministic local evaluations for open demo trades.",
	)
	demo_trade_evaluation_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_hypothesis_performance_summary_parser = subparsers.add_parser(
		"demo-hypothesis-performance-summary",
		help="Append deterministic demo evidence summaries grouped by source hypothesis.",
	)
	demo_hypothesis_performance_summary_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_promotion_board_parser = subparsers.add_parser(
		"demo-promotion-board",
		help="Show a read-only demo promotion board for one symbol.",
	)
	demo_promotion_board_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_monitoring_cycle_parser = subparsers.add_parser(
		"demo-monitoring-cycle",
		help="Run the safe demo monitoring and evaluation cycle for one symbol.",
	)
	demo_monitoring_cycle_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_current_opportunity_rating_parser = subparsers.add_parser(
		"demo-current-opportunity-rating",
		help="Show read-only current opportunity ratings for one symbol.",
	)
	demo_current_opportunity_rating_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_status_dashboard_parser = subparsers.add_parser(
		"demo-status-dashboard",
		help="Show the read-only latest local demo status dashboard for one symbol.",
	)
	demo_status_dashboard_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_daily_operator_parser = subparsers.add_parser(
		"demo-daily-operator",
		help="Run the safe demo monitoring cycle and status dashboard for one symbol.",
	)
	demo_daily_operator_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_daily_operator_parser.add_argument(
		"--ai-review",
		action="store_true",
		help="Request the advisory daily AI review after monitoring; confirmation is still required.",
	)
	demo_daily_operator_parser.add_argument(
		"--confirm-ai-call",
		action="store_true",
		help="Explicitly allow one advisory AI call when --ai-review is also present.",
	)

	demo_exit_readiness_parser = subparsers.add_parser(
		"demo-exit-readiness",
		help="Show read-only exit readiness for open demo trades.",
	)
	demo_exit_readiness_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_ai_review_trigger_parser = subparsers.add_parser(
		"demo-ai-review-trigger",
		help="Decide whether local demo evidence warrants AI review without calling AI.",
	)
	demo_ai_review_trigger_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_daily_ai_review_parser = subparsers.add_parser(
		"demo-daily-ai-review",
		help="Run one confirmation-gated advisory AI review of local demo state.",
	)
	demo_daily_ai_review_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	demo_daily_ai_review_parser.add_argument(
		"--confirm-ai-call",
		action="store_true",
		help="Explicitly allow one advisory AI call if this local state is not already reviewed.",
	)

	demo_daily_ai_reviews_parser = subparsers.add_parser(
		"demo-daily-ai-reviews",
		help="Show stored daily demo AI reviews for one symbol without calling AI.",
	)
	demo_daily_ai_reviews_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	demo_operator_runbook_parser = subparsers.add_parser(
		"demo-operator-runbook",
		help="Print the read-only daily demo operator runbook for one symbol.",
	)
	demo_operator_runbook_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)

	research_cycle_parser = subparsers.add_parser(
		"research-cycle",
		help="Preview the next safe research steps for one symbol.",
	)
	research_cycle_parser.add_argument(
		"symbol",
		nargs="?",
		default=DEFAULT_SYMBOL,
		help=f"Symbol to process (default: {DEFAULT_SYMBOL}).",
	)
	research_cycle_mode_group = research_cycle_parser.add_mutually_exclusive_group()
	research_cycle_mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview the research cycle without modifying records (default).",
	)
	research_cycle_mode_group.add_argument(
		"--reviews",
		action="store_true",
		help="Run review-only orchestration for planned hypothesis-review actions.",
	)
	research_cycle_mode_group.add_argument(
		"--planned-experiments",
		action="store_true",
		help="Run experiment request generation only for hypotheses selected by the research plan.",
	)
	research_cycle_mode_group.add_argument(
		"--run-experiments",
		action="store_true",
		help="Run deterministic execution for currently executable experiment requests.",
	)
	research_cycle_mode_group.add_argument(
		"--revisions",
		action="store_true",
		help="Run revision proposal generation only for hypotheses selected by the research plan.",
	)
	research_cycle_mode_group.add_argument(
		"--full-safe",
		action="store_true",
		help="Run the full safe orchestration chain without applying revisions or creating child hypotheses.",
	)

	hypothesis_revision_apply_parser = subparsers.add_parser(
		"hypothesis-revision-apply",
		help="Apply one hypothesis revision proposal in dry-run or apply mode.",
	)
	hypothesis_revision_apply_parser.add_argument(
		"symbol",
		help="Symbol to process.",
	)
	hypothesis_revision_apply_parser.add_argument(
		"proposal_id",
		help="Revision proposal identifier.",
	)
	mode_group = hypothesis_revision_apply_parser.add_mutually_exclusive_group()
	mode_group.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview application without creating a child hypothesis (default).",
	)
	mode_group.add_argument(
		"--apply",
		action="store_true",
		help="Apply proposal and append a child hypothesis if eligible.",
	)

	return parser


def main(argv=None):
	parser = _build_arg_parser()

	if argv is None:
		argv = sys.argv[1:]

	if not argv:
		parser.print_help()
		return 0

	args = parser.parse_args(argv)

	if args.mode == "hypotheses":
		run_manual_hypothesis_generation(symbol=args.symbol)
		return 0

	if args.mode == "experiment-requests":
		run_manual_experiment_request_generation(
			symbol=args.symbol,
			planned_only=args.planned_only,
		)
		return 0

	if args.mode == "experiment-execution":
		experiment_execution_kwargs = {
			"symbol": args.symbol,
		}

		if args.period is not None:
			experiment_execution_kwargs["period"] = args.period

		if args.interval is not None:
			experiment_execution_kwargs["interval"] = args.interval

		run_manual_experiment_execution(**experiment_execution_kwargs)
		return 0

	if args.mode == "hypothesis-evaluation":
		run_manual_hypothesis_evaluation(symbol=args.symbol)
		return 0

	if args.mode == "hypothesis-reviews":
		run_manual_hypothesis_reviews(symbol=args.symbol)
		return 0

	if args.mode == "hypothesis-lifecycle":
		run_manual_hypothesis_lifecycle(symbol=args.symbol)
		return 0

	if args.mode == "hypothesis-revisions":
		run_manual_hypothesis_revisions(symbol=args.symbol)
		return 0

	if args.mode == "research-plan":
		run_manual_research_plan(symbol=args.symbol)
		return 0

	if args.mode == "research-state":
		run_manual_research_state(symbol=args.symbol)
		return 0

	if args.mode == "research-dashboard":
		run_manual_research_dashboard(symbols=args.symbols)
		return 0

	if args.mode == "research-freshness":
		run_manual_research_freshness(symbol=args.symbol)
		return 0

	if args.mode == "promotion-candidates":
		run_manual_promotion_candidates(symbol=args.symbol)
		return 0

	if args.mode == "trade-candidate-proposals":
		run_manual_trade_candidate_proposals(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-candidates":
		run_manual_demo_trade_candidates(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-candidate-generation":
		run_manual_demo_trade_candidate_generation(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-gate":
		run_manual_demo_trade_gate(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-gate-apply":
		run_manual_demo_trade_gate_apply(
			symbol=args.symbol,
			apply_changes=bool(args.apply),
		)
		return 0

	if args.mode == "demo-trade-queue":
		run_manual_demo_trade_queue(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-queue-add":
		run_manual_demo_trade_queue_add(
			symbol=args.symbol,
			apply_changes=bool(args.apply),
		)
		return 0

	if args.mode == "demo-order-intents":
		run_manual_demo_order_intents(symbol=args.symbol)
		return 0

	if args.mode == "demo-order-intent-add":
		run_manual_demo_order_intent_add(
			symbol=args.symbol,
			apply_changes=bool(args.apply),
		)
		return 0

	if args.mode == "demo-paper-order-submit":
		run_manual_demo_paper_order_submit(
			symbol=args.symbol,
			apply_changes=bool(args.apply),
			confirm_paper_submit=bool(args.confirm_paper_submit),
		)
		return 0

	if args.mode == "demo-broker-readiness":
		run_manual_demo_broker_readiness()
		return 0

	if args.mode == "demo-broker-account":
		run_manual_demo_broker_account()
		return 0

	if args.mode == "demo-broker-order-status-sync":
		run_manual_demo_broker_order_status_sync(symbol=args.symbol)
		return 0

	if args.mode == "demo-position-snapshot":
		run_manual_demo_position_snapshot(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-performance-snapshot":
		run_manual_demo_trade_performance_snapshot(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-performance-dashboard":
		run_manual_demo_trade_performance_dashboard(symbol=args.symbol)
		return 0

	if args.mode == "demo-trade-evaluation":
		run_manual_demo_trade_evaluation(symbol=args.symbol)
		return 0

	if args.mode == "demo-hypothesis-performance-summary":
		run_manual_demo_hypothesis_performance_summary(symbol=args.symbol)
		return 0

	if args.mode == "demo-promotion-board":
		run_manual_demo_promotion_board(symbol=args.symbol)
		return 0

	if args.mode == "demo-monitoring-cycle":
		run_manual_demo_monitoring_cycle(symbol=args.symbol)
		return 0

	if args.mode == "demo-current-opportunity-rating":
		run_manual_demo_current_opportunity_rating(symbol=args.symbol)
		return 0

	if args.mode == "demo-status-dashboard":
		run_manual_demo_status_dashboard(symbol=args.symbol)
		return 0

	if args.mode == "demo-daily-operator":
		run_manual_demo_daily_operator(
			symbol=args.symbol,
			ai_review_requested=bool(args.ai_review),
			confirm_ai_call=bool(args.confirm_ai_call),
		)
		return 0

	if args.mode == "demo-exit-readiness":
		run_manual_demo_exit_readiness(symbol=args.symbol)
		return 0

	if args.mode == "demo-ai-review-trigger":
		run_manual_demo_ai_review_trigger(symbol=args.symbol)
		return 0

	if args.mode == "demo-daily-ai-review":
		run_manual_demo_daily_ai_review(
			symbol=args.symbol,
			confirm_ai_call=bool(args.confirm_ai_call),
		)
		return 0

	if args.mode == "demo-daily-ai-reviews":
		run_manual_demo_daily_ai_reviews(symbol=args.symbol)
		return 0

	if args.mode == "demo-operator-runbook":
		run_manual_demo_operator_runbook(symbol=args.symbol)
		return 0

	if args.mode == "research-cycle":
		run_manual_research_cycle(
			symbol=args.symbol,
			dry_run=not (
				args.reviews
				or args.planned_experiments
				or args.run_experiments
				or args.revisions
				or args.full_safe
			),
			reviews=bool(args.reviews),
			planned_experiments=bool(args.planned_experiments),
			run_experiments=bool(args.run_experiments),
			revisions=bool(args.revisions),
			full_safe=bool(args.full_safe),
		)
		return 0

	if args.mode == "hypothesis-revision-apply":
		run_manual_hypothesis_revision_apply(
			symbol=args.symbol,
			proposal_id=args.proposal_id,
			apply_changes=bool(args.apply),
		)
		return 0

	parser.print_help()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
