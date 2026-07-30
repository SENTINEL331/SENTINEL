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