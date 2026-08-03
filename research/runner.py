import argparse
import json
import sys

from ai.experiment_request_service import ExperimentRequestService
from ai.hypothesis_service import HypothesisService
from ai.journal import ResearchJournal
from ai.storage import Storage
from research.executor import ExperimentExecutor
from research.experiment_result import ExperimentResultStatus


DEFAULT_SYMBOL = "NVDA"


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
	skipped_count = 0

	for request in experiment_requests:
		if request.symbol and request.symbol != symbol:
			skipped_count += 1
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
	print(f"Requests Loaded : {len(experiment_requests)}")
	print(f"Requests Executed : {len(experiment_results)}")
	print(f"Requests Skipped : {skipped_count}")
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

	else:
		print()
		print("No experiment requests to execute.")

	return experiment_results


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

	parser.print_help()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
