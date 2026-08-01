class ResearchSnapshot:
    """Represents everything Sentinel currently knows about one market."""

    def __init__(
        self,
        symbol,
        date,
        open_price,
        high,
        low,
        close,
        volume,
        measurements,
    ):

        self.symbol = symbol

        self.date = date

        self.open = open_price

        self.high = high

        self.low = low

        self.close = close

        self.volume = volume

        self.measurements = measurements

    def get(
        self,
        name,
    ):
        """Return a measurement by name."""

        return self.measurements.get(name)

    def has(
        self,
        name,
    ):
        """Return True if a measurement exists."""

        return name in self.measurements

    def list_measurements(self):
        """Return all available measurements."""

        return list(self.measurements.keys())