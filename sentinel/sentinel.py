from config.settings import WATCHLIST

from analytics.feature_store import FeatureStore

from research.snapshot import ResearchSnapshot

from sentinel.capabilities import CAPABILITIES


class Sentinel:
    """Provides the interface between Sentinel and the AI."""

    def __init__(self):

        self.features = FeatureStore()

    def get_watchlist(self):
        """Return the configured watchlist."""

        return WATCHLIST

    def list_capabilities(self):
        """Return available Sentinel capabilities."""

        return list(CAPABILITIES.keys())

    def get_snapshot(
        self,
        symbol,
    ):
        """Return the latest market snapshot."""

        data = self.features.load_features(symbol)

        latest = data.iloc[-1]

        measurements = {

            column: latest[column]

            for column in data.columns

            if column not in (
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            )

        }

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