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

    def research(self):
        """
        Begin one research cycle.
        """

        watchlist = self.sentinel.get_watchlist()

        print()

        print("=" * 50)
        print("AI Research Cycle")
        print("=" * 50)

        for symbol in watchlist:

            snapshot = self.sentinel.get_snapshot(symbol)

            print(f"Reviewing {snapshot.symbol}")

        print()

        print("Research cycle complete.")