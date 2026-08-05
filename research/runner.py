import argparse
import json
import sys

from config import settings

from ai.experiment_request_service import ExperimentRequestService
from ai.hypothesis_revision_application_service import HypothesisRevisionApplicationService
from ai.hypothesis_revision_service import HypothesisRevisionService
from ai.hypothesis_service import HypothesisService
from ai.hypothesis_review_service import HypothesisReviewService
from ai.journal import ResearchJournal
from ai.storage import Storage
from research.executor import ExperimentExecutor
from research.experiment import ExperimentRequestExecutionState
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.research_freshness import ProposalFreshnessStatus
from research.research_freshness import ReviewFreshnessStatus
from research.research_freshness import build_research_freshness
from research.research_plan import ResearchPlanAction
from research.research_plan import ResearchPlanPriority
from research.research_plan import build_research_plan


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
	if any(
		item.review_freshness in {
			ReviewFreshnessStatus.MISSING,
			ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT,
			ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION,
		}
		for item in freshness_items
	):
		suggestions.append(f"python -m research.runner research-cycle {symbol} --reviews")

	if any(
		item.proposal_freshness in {
			ProposalFreshnessStatus.MISSING_FOR_REFINE_CANDIDATE,
			ProposalFreshnessStatus.STALE_AFTER_REVIEW,
		}
		for item in freshness_items
	):
		suggestions.append(f"python -m research.runner research-cycle {symbol} --revisions")

	if suggestions:
		for suggestion in suggestions:
			print(f"- {suggestion}")
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

	def _completed_request_ids_for_results(experiment_results):
		return {
			result.experiment_request_id
			for result in experiment_results
			if result.status == ExperimentResultStatus.COMPLETED and result.experiment_request_id
		}

	for symbol in reviewed_symbols:
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
				"plan_items": len(research_plan.items),
				"highest_priority": highest_priority,
				"top_action": top_action,
				"action_counts": per_symbol_action_counts,
			}
		)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST.value] > 0:
			suggested_commands.append(
				f"python -m research.runner research-cycle {symbol} --planned-experiments"
			)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW.value] > 0:
			suggested_commands.append(
				f"python -m research.runner research-cycle {symbol} --reviews"
			)

		if per_symbol_action_counts[ResearchPlanAction.GENERATE_REVISION_PROPOSAL.value] > 0:
			suggested_commands.append(
				f"python -m research.runner research-cycle {symbol} --revisions"
			)

		if pending_executable_request_count > 0:
			suggested_commands.append(
				f"python -m research.runner research-cycle {symbol} --run-experiments"
			)

		if per_symbol_action_counts[ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE.value] > 0:
			suggested_commands.append(
				f"python -m research.runner hypothesis-revision-apply {symbol} <proposal_id> --dry-run"
			)

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

		if any(
			summary["action_counts"][ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE.value] > 0
			for summary in symbol_summaries
		):
			print(
				"- Note: hypothesis-revision-apply requires a concrete proposal_id and explicit human choice."
			)
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
):
	"""Run one-symbol experiment execution on demand using stored requests."""

	storage = storage or Storage()
	executor = executor or ExperimentExecutor()
	execution_summary = _execute_experiment_requests_for_symbol(
		symbol=symbol,
		storage=storage,
		executor=executor,
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

	else:
		print()
		print("No experiment requests to execute.")

	return experiment_results


def _execute_experiment_requests_for_symbol(
	symbol,
	storage,
	executor,
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

		experiment_results.append(executor.execute(request))

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
		run_manual_experiment_execution(symbol=args.symbol)
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
