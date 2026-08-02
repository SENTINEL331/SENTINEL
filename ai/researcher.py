from datetime import date

from research.memory import ResearchMemory
from research.record import ResearchRecord


class Researcher:
    """
    Represents the AI researcher.

    The Researcher reviews market evidence,
    develops hypotheses,
    requests experiments,
    and manages research.

    The Researcher never executes experiments directly.
    """

    def __init__(
        self,
        sentinel,
    ):

        self.sentinel = sentinel

        self.memory = ResearchMemory()

    def research(self):
        """Begin one research cycle."""

        watchlist = self.sentinel.get_watchlist()

        capabilities = self.sentinel.list_capabilities()

        print()
        print("=" * 50)
        print("AI Research Cycle")
        print("=" * 50)

        print()
        print(f"Capabilities Available : {len(capabilities)}")

        ready = 0

        for symbol in watchlist:

            print()
            print("=" * 50)
            print(symbol)
            print("=" * 50)

            #
            # Evidence
            #

            print()
            print("Evidence")
            print("-" * 8)

            snapshot = self.sentinel.get_snapshot(symbol)

            print("✓ Market snapshot reviewed")

            #
            # Research
            #

            record = ResearchRecord(
                symbol=snapshot.symbol,
                category="Snapshot",
                summary="Latest market snapshot reviewed.",
                created=str(date.today()),
            )

            self.memory.add(record)

            print()
            print("Research")
            print("-" * 8)

            print(f"Research Records : {len(self.memory.get_symbol(symbol))}")

            #
            # Status
            #

            print()
            print("Status")
            print("-" * 6)

            print("✓ Research Active")

            ready += 1

        #
        # Daily Summary
        #

        print()
        print("=" * 50)
        print("Daily Summary")
        print("=" * 50)

        print(f"Symbols Reviewed : {ready}")
        print(f"Research Records : {self.memory.count()}")

        print()
        print("Research Cycle Complete")