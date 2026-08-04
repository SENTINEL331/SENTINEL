import argparse
import json
import sys

from ai.experiment_request_service import ExperimentRequestService
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

	experiment_requests = experiment_request_service.generate_for_symbol(
		symbol=symbol,
		journal=journal_text,
		hypotheses=hypotheses,
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


def run_manual_experiment_execution(
	symbol=DEFAULT_SYMBOL,
	storage=None,
	executor=None,
):
	"""Run one-symbol experiment execution on demand using stored requests."""

	storage = storage or Storage()
	executor = executor or ExperimentExecutor()

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

	print()
	print("=" * 50)
	print(f"Manual Experiment Execution: {symbol}")
	print("=" * 50)
	print()
	total_skipped_count = (
		skipped_symbol_mismatch_count
		+ skipped_non_executable_count
		+ skipped_obsolete_count
	)
	print(f"Requests Loaded : {len(experiment_requests)}")
	print(f"Requests Executed : {len(experiment_results)}")
	print(f"Requests Skipped : {total_skipped_count}")
	print(f"Skipped Non-Executable : {skipped_non_executable_count}")
	print(f"Skipped Obsolete : {skipped_obsolete_count}")
	print(f"Skipped Symbol Mismatch : {skipped_symbol_mismatch_count}")
	print(f"Results Saved : {len(experiment_results)}")
	print(f"Not Implemented : {not_implemented_count}")

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
		run_manual_experiment_request_generation(symbol=args.symbol)
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

	parser.print_help()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
