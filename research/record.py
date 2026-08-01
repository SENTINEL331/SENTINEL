class ResearchRecord:
    """Represents one piece of research produced by the AI."""

    def __init__(
        self,
        symbol,
        category,
        summary,
        created,
    ):

        self.symbol = symbol

        self.category = category

        self.summary = summary

        self.created = created