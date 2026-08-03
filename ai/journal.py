from ai.storage import Storage


class ResearchJournal:
    """
    Builds the AI's research journal from
    Sentinel's persistent stores.
    """

    def __init__(self):

        self.storage = Storage()

    def build(
        self,
        symbol,
    ):
        """
        Build a journal for one symbol.
        """

        observations = self.storage.load_observations(symbol)

        lines = []

        lines.append(f"Research Journal: {symbol}")
        lines.append("")
        lines.append("Observations")
        lines.append("------------")

        if observations:

            for observation in observations:

                lines.append(
                    f"- {observation.statement}"
                )

        else:

            lines.append(
                "No previous observations."
            )

        return "\n".join(lines)