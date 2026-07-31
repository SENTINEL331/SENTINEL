from pathlib import Path
import pandas as pd

from config.settings import DEFAULT_INTERVAL


class FeatureStore:
    """Stores calculated market features."""

    def save_features(
        self,
        data,
        symbol,
        interval=DEFAULT_INTERVAL,
    ):
        """Save calculated features."""

        data_directory = Path("data/features")
        data_directory.mkdir(parents=True, exist_ok=True)

        filename = f"{symbol}_{interval.upper()}_FEATURES.csv"
        filepath = data_directory / filename

        data.to_csv(filepath, index=False)

        return filepath

    def load_features(
        self,
        symbol,
        interval=DEFAULT_INTERVAL,
    ):
        """Load calculated features."""

        filepath = Path("data/features") / (
            f"{symbol}_{interval.upper()}_FEATURES.csv"
        )

        return pd.read_csv(filepath)

    def features_exist(
        self,
        symbol,
        interval=DEFAULT_INTERVAL,
    ):
        """Check whether calculated features exist."""

        filepath = Path("data/features") / (
            f"{symbol}_{interval.upper()}_FEATURES.csv"
        )

        return filepath.exists()

    def get_latest_feature_date(
        self,
        symbol,
        interval=DEFAULT_INTERVAL,
    ):
        """Return the latest feature date."""

        data = self.load_features(symbol, interval)

        data["Date"] = pd.to_datetime(data["Date"])

        return data["Date"].max()

    def get_feature_status(
        self,
        symbol,
        interval=DEFAULT_INTERVAL,
    ):
        """Return feature availability information."""

        exists = self.features_exist(symbol, interval)

        if not exists:

            return {
                "exists": False,
                "latest_date": None,
                "status": "Missing",
            }

        latest = self.get_latest_feature_date(
            symbol,
            interval,
        )

        return {
            "exists": True,
            "latest_date": latest,
            "status": "Available",
        }