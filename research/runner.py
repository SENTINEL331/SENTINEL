import argparse
import json
import sys

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
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.research_plan import ResearchPlanAction
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


def run_manual_research_cycle(
	symbol=DEFAULT_SYMBOL,
	dry_run=True,
	reviews=False,
	planned_experiments=False,
	run_experiments=False,
	storage=None,
	hypothesis_review_service=None,
	experiment_request_service=None,
	executor=None,
	journal=None,
):
	"""Run a manual research cycle in one explicit orchestration mode."""

	selected_modes = [dry_run, reviews, planned_experiments, run_experiments]
	if sum(1 for enabled in selected_modes if enabled) != 1:
		raise ValueError(
			"research-cycle mode is mutually exclusive: choose exactly one of dry-run, reviews, planned-experiments, or run-experiments"
		)

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

			updated_hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
			updated_latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(updated_hypothesis_reviews)
			updated_lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
				hypotheses=hypotheses,
				evidence_summaries=evidence_summaries,
				latest_reviews_by_hypothesis_id=updated_latest_reviews_by_hypothesis_id,
			)
			final_plan = build_research_plan(
				symbol=symbol,
				hypotheses=hypotheses,
				experiment_requests=experiment_requests,
				experiment_results=experiment_results,
				evidence_summaries=evidence_summaries,
				latest_reviews_by_hypothesis_id=updated_latest_reviews_by_hypothesis_id,
				lifecycle_recommendations=updated_lifecycle_recommendations,
				revision_proposals=revision_proposals,
				revision_applications=revision_applications,
			)

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

			updated_experiment_requests = storage.load_experiment_requests(symbol)
			updated_lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
				hypotheses=hypotheses,
				evidence_summaries=evidence_summaries,
				latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
			)
			final_plan = build_research_plan(
				symbol=symbol,
				hypotheses=hypotheses,
				experiment_requests=updated_experiment_requests,
				experiment_results=experiment_results,
				evidence_summaries=evidence_summaries,
				latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
				lifecycle_recommendations=updated_lifecycle_recommendations,
				revision_proposals=revision_proposals,
				revision_applications=revision_applications,
			)

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

		updated_experiment_requests = storage.load_experiment_requests(symbol)
		updated_experiment_results = storage.load_experiment_results(symbol)
		updated_evidence_summaries = evaluate_hypothesis_evidence(
			hypotheses=hypotheses,
			experiment_results=updated_experiment_results,
			experiment_requests=updated_experiment_requests,
		)
		updated_lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
			hypotheses=hypotheses,
			evidence_summaries=updated_evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
		)
		final_plan = build_research_plan(
			symbol=symbol,
			hypotheses=hypotheses,
			experiment_requests=updated_experiment_requests,
			experiment_results=updated_experiment_results,
			evidence_summaries=updated_evidence_summaries,
			latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
			lifecycle_recommendations=updated_lifecycle_recommendations,
			revision_proposals=revision_proposals,
			revision_applications=revision_applications,
		)

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

	if args.mode == "research-cycle":
		run_manual_research_cycle(
			symbol=args.symbol,
			dry_run=not (args.reviews or args.planned_experiments or args.run_experiments),
			reviews=bool(args.reviews),
			planned_experiments=bool(args.planned_experiments),
			run_experiments=bool(args.run_experiments),
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
