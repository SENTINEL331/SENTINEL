import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):
        return False

load_dotenv()

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

DEMO_BROKER = os.getenv("DEMO_BROKER", "")
DEMO_BROKER_MODE = os.getenv("DEMO_BROKER_MODE", "demo")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
DEMO_DEFAULT_ORDER_NOTIONAL = float(os.getenv("DEMO_DEFAULT_ORDER_NOTIONAL", "100.00"))
DEMO_MAX_ORDER_NOTIONAL = float(os.getenv("DEMO_MAX_ORDER_NOTIONAL", "100.00"))
DEMO_TRADE_EVALUATION_WINDOW_TRADING_DAYS = int(
    os.getenv("DEMO_TRADE_EVALUATION_WINDOW_TRADING_DAYS", "5")
)


def get_demo_broker_settings() -> dict[str, str]:
    """Return demo broker configuration used by readiness and account checks."""

    return {
        "broker": DEMO_BROKER,
        "mode": DEMO_BROKER_MODE,
        "base_url": ALPACA_BASE_URL,
        "api_key": ALPACA_API_KEY,
        "secret_key": ALPACA_SECRET_KEY,
    }

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
