from research.memory import ResearchMemory
from research.parser import parse_observations

from config.settings import ENABLE_HYPOTHESIS_GENERATION
from ai.client import AIClient
from ai.hypothesis_service import HypothesisService
from ai.journal import ResearchJournal
from ai.storage import Storage


class Researcher:
    """
    Sentinel's autonomous AI researcher.
    """

    def __init__(self, sentinel):

        self.sentinel = sentinel

        self.memory = ResearchMemory()

        self.ai = AIClient()

        self.storage = Storage()

        self.journal = ResearchJournal()

        self.hypothesis_service = HypothesisService(
            ai_client=self.ai,
            storage=self.storage,
        )

    def research(self):

        watchlist = self.sentinel.get_watchlist()

        print()
        print("=" * 50)
        print("AI Research Cycle")
        print("=" * 50)

        symbols_processed = 0

        for symbol in watchlist:

            print()
            print("=" * 50)
            print(symbol)
            print("=" * 50)

            #
            # Evidence
            #

            snapshot = self.sentinel.get_snapshot(symbol)

            print()
            print("Evidence")
            print("-" * 8)

            print("✓ Snapshot collected")

            #
            # AI Research
            #

            print()
            print("AI")
            print("-" * 2)

            response = self.ai.observe(snapshot)

            observations = parse_observations(
                snapshot,
                response,
            )

            #
            # Memory
            #

            for observation in observations:

                self.memory.add(observation)

                print(f"• {observation.statement}")

            #
            # Persistent Storage
            #

            self.storage.save_observations(
                symbol,
                observations,
            )

            print()
            print("Storage")
            print("-" * 7)

            print(f"✓ Saved {len(observations)} observations")

            if ENABLE_HYPOTHESIS_GENERATION:

                journal_text = self.journal.build(symbol)

                hypotheses = self.hypothesis_service.generate_for_symbol(
                    symbol=symbol,
                    journal=journal_text,
                    observations=observations,
                    snapshot_text=snapshot.to_text(),
                )

                print(f"✓ Generated {len(hypotheses)} hypotheses")

            #
            # Status
            #

            print()
            print("Status")
            print("-" * 6)

            print("✓ Research complete")

            symbols_processed += 1

        print()
        print("=" * 50)
        print("Research Summary")
        print("=" * 50)

        print(f"Symbols Reviewed : {symbols_processed}")
        print(f"Observations Stored : {self.memory.count()}")

        print()
        print("Research cycle complete.")