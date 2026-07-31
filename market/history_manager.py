from pathlib import Path
import pandas as pd

from config.settings import DEFAULT_INTERVAL


class HistoryManager:
    """Handles historical market data storage."""

    def save_history(self, data, symbol, interval=DEFAULT_INTERVAL):
        """Save historical market data to a CSV file."""

        data_directory = Path("data/raw")
        data_directory.mkdir(parents=True, exist_ok=True)

        filename = f"{symbol}_{interval.upper()}.csv"
        filepath = data_directory / filename

        data.to_csv(filepath)

        return filepath

    def load_history(self, symbol, interval=DEFAULT_INTERVAL):
        """Load historical market data from a CSV file."""

        filepath = Path("data/raw") / f"{symbol}_{interval.upper()}.csv"

        return pd.read_csv(filepath)

    def get_latest_date(self, symbol, interval=DEFAULT_INTERVAL):
        """Return the most recent date in the historical data."""

        data = self.load_history(symbol, interval)

        data["Date"] = pd.to_datetime(data["Date"])

        return data["Date"].max()

    def history_exists(self, symbol, interval=DEFAULT_INTERVAL):
        """Check whether historical data already exists."""

        filepath = Path("data/raw") / f"{symbol}_{interval.upper()}.csv"

        return filepath.exists()