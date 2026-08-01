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
        """
        Begin one research cycle.
        """

        watchlist = self.sentinel.get_watchlist()

        print()
        print("=" * 50)
        print("AI Research Cycle")
        print("=" * 50)
        print()

        for symbol in watchlist:

            print(f"Reviewing {symbol}...")

            snapshot = self.sentinel.get_snapshot(symbol)

            record = ResearchRecord(
                symbol=snapshot.symbol,
                category="Snapshot",
                summary="Latest market snapshot reviewed.",
                created=str(date.today()),
            )

            self.memory.add(record)

            print("✓ Snapshot Reviewed")
            print()

        print("=" * 50)
        print("Research Summary")
        print("=" * 50)

        print(f"Symbols Reviewed : {len(watchlist)}")
        print(f"Research Records : {self.memory.count()}")

        print()
        print("Research cycle complete.")