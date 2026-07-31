import yfinance as yf
from pathlib import Path
from config.settings import VERSION, DATA_PROVIDER, DEFAULT_PERIOD, DEFAULT_INTERVAL

class MarketDataManager:
    """Handles historical market data for Sentinel."""

    def __init__(self):
        self.version = VERSION
        self.provider = DATA_PROVIDER
        self.status = "Market Module Online"

    def get_provider(self):
        return self.provider

    def get_version(self):
        return self.version

    def get_status(self):
        return self.status

    def download_history(
        self,
        symbol,
        period=DEFAULT_PERIOD,
        interval=DEFAULT_INTERVAL,
    ):
        """Download historical market data from Yahoo Finance."""

        data = yf.download(
            symbol,
            period=period,
            interval=interval,
        )

        return data

    def save_history(self, data, symbol, interval="1d"):
        """Save historical market data to a CSV file."""

        data_directory = Path("data/raw")
        data_directory.mkdir(parents=True, exist_ok=True)

        filename = f"{symbol}_{interval.upper()}.csv"
        filepath = data_directory / filename

        data.to_csv(filepath)

        return filepath
    
    def history_exists(self, symbol, interval=DEFAULT_INTERVAL):
        """Check whether historical data already exists."""

        filepath = Path("data/raw") / f"{symbol}_{interval.upper()}.csv"

        return filepath.exists()