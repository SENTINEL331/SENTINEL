import os

APP_NAME = "Sentinel"
VERSION = "v1.0"
AI_MODEL = "gpt-5"
ENABLE_HYPOTHESIS_GENERATION = False

DATA_PROVIDER = "Yahoo Finance"

WATCHLIST = [
    "NVDA",
    "AAPL",
    "MSFT",
    "TSLA",
]

DEFAULT_PERIOD = "30d"
DEFAULT_INTERVAL = "1d"
BACKTEST_PERIOD = "2y"
BACKTEST_INTERVAL = "1d"

BROKER_MODE = os.getenv("BROKER_MODE", "demo")
BROKER_BASE_URL = os.getenv("BROKER_BASE_URL", "")
BROKER_API_KEY = os.getenv("BROKER_API_KEY", "")
BROKER_API_SECRET = os.getenv("BROKER_API_SECRET", "")

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
    {
        "name": "ATR",
        "parameters": {
            "period": 14,
        },
    },
    {
        "name": "BOLLINGER",
        "parameters": {
            "period": 20,
            "deviations": 2,
        },
    },
]
