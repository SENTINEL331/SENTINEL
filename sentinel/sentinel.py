from market.history_manager import HistoryManager

from analytics.feature_store import FeatureStore
from analytics.feature_registry import FeatureRegistry

from research.snapshot import ResearchSnapshot

from config.settings import WATCHLIST


class Sentinel:
    """Primary interface between Sentinel and the AI."""

    def __init__(self):

        self.history = HistoryManager()

        self.features = FeatureStore()

        self.registry = FeatureRegistry()

    def get_watchlist(self):
        """Return the configured watchlist."""

        return WATCHLIST

    def list_measurements(self):
        """Return all available measurements."""

        return self.registry.list_features()

    def get_snapshot(
        self,
        symbol,
    ):
        """Return the latest market snapshot for a symbol."""

        data = self.features.load_features(symbol)

        latest = data.iloc[-1]

        measurements = {}

        for column in data.columns:

            if column in [
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]:
                continue

            measurements[column] = latest[column]

        return ResearchSnapshot(
            symbol=symbol,
            date=latest["Date"],
            open_price=latest["Open"],
            high=latest["High"],
            low=latest["Low"],
            close=latest["Close"],
            volume=latest["Volume"],
            measurements=measurements,
        )