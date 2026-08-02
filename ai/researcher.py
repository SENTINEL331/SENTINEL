from research.memory import ResearchMemory
from research.parser import parse_observations

from ai.client import AIClient


class Researcher:
    """
    Represents Sentinel's autonomous AI researcher.
    """

    def __init__(
        self,
        sentinel,
    ):

        self.sentinel = sentinel

        self.memory = ResearchMemory()

        self.ai = AIClient()

    def research(self):
        """Run one complete AI research cycle."""

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
            # AI Observation
            #

            print()
            print("AI")
            print("-" * 2)

            response = self.ai.observe(snapshot)

            records = parse_observations(
                snapshot.symbol,
                response,
            )

            for record in records:

                self.memory.add(record)

                print(f"• {record.summary}")

            #
            # Status
            #

            print()
            print("Status")
            print("-" * 6)

            print(
                f"✓ {len(records)} observations stored"
            )

            symbols_processed += 1

        #
        # Summary
        #

        print()
        print("=" * 50)
        print("Research Summary")
        print("=" * 50)

        print(f"Symbols Reviewed : {symbols_processed}")
        print(f"Research Records : {self.memory.count()}")

        print()
        print("Research cycle complete.")