import yfinance as yf

class MarketDataManager:
    """Handles historical market data for Sentinel."""

    def __init__(self):
        self.provider = "MetaTrader 5"
        self.version = "0.1"
        self.status = "Market Module Online"

    def get_provider(self):
        return self.provider

    def get_version(self):
        return self.version

    def get_status(self):
        return self.status

    def download_history(self, symbol, period="30d", interval="1d"):
        """Download historical market data from Yahoo Finance."""

        data = yf.download(
            symbol,
            period=period,
            interval=interval
        )

        return data