APP_NAME = "Sentinel"
VERSION = "v0.9"

DATA_PROVIDER = "Yahoo Finance"

WATCHLIST = [
    "NVDA",
    "AAPL",
    "MSFT",
    "TSLA",
]

DEFAULT_PERIOD = "30d"
DEFAULT_INTERVAL = "1d"

FEATURE_SET = [
    {
        "name": "SMA",
        "parameters": {
            "period": 20,
        },
    },
    {
        "name": "EMA",
        "parameters": {
            "period": 20,
        },
    },
    {
        "name": "RSI",
        "parameters": {
            "period": 14,
        },
    },
]