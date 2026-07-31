import yfinance as yf
import pandas as pd
from pathlib import Path
from config.settings import VERSION, DATA_PROVIDER, DEFAULT_PERIOD, DEFAULT_INTERVAL

class MarketDataManager:
    """Handles historical market data for Sentinel."""

    # ============================================
    # Initialisation
    # ============================================

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

    # ============================================
    # Download
    # ============================================

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

        # Flatten the Yahoo Finance DataFramed
        data.columns = data.columns.get_level_values(0)

        # Move the index (Date) into a normal column
        data.reset_index(inplace=True)

        return data