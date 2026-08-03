from ai.hypothesis_service import HypothesisService
from ai.journal import ResearchJournal
from ai.storage import Storage


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


def main():
	run_manual_hypothesis_generation()


if __name__ == "__main__":
	main()
