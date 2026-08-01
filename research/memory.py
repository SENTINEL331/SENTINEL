from research.record import ResearchRecord


class ResearchMemory:
    """Stores all research records."""

    def __init__(self):

        self.records = []

    def add(
        self,
        record,
    ):
        """Add a research record."""

        self.records.append(record)

    def get_all(self):
        """Return every research record."""

        return self.records

    def get_symbol(
        self,
        symbol,
    ):
        """Return research for one symbol."""

        return [

            record

            for record in self.records

            if record.symbol == symbol

        ]

    def count(self):
        """Return total number of records."""

        return len(self.records)