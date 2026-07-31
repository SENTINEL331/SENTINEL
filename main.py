from market.data_manager import MarketDataManager
from market.history_manager import HistoryManager

from analytics.feature_engine import FeatureEngine
from analytics.feature_store import FeatureStore

from utils.banner import show_banner
from utils.logger import setup_logger

from config.settings import WATCHLIST


def main():
    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()
    history = HistoryManager()
    features = FeatureStore()

    show_banner()

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    for symbol in WATCHLIST:

        # Check historical data
        history_status = history.get_history_status(symbol)

        logger.info(f"{symbol}: {history_status}")

        if not history_status["exists"]:

            logger.info(f"{symbol}: No data found.")
            logger.info(f"Downloading {symbol}...")

            data = manager.download_history(symbol)

            filepath = history.save_history(data, symbol)

            logger.info(f"Data saved to {filepath}")

        # Load historical data
        data = history.load_history(symbol)

        # Check feature data
        feature_status = features.get_feature_status(symbol)

        logger.info(f"{symbol} Features: {feature_status}")

        if feature_status["exists"]:

            logger.info(f"{symbol}: Loading existing features...")

            data = features.load_features(symbol)

        else:

            logger.info(f"{symbol}: Calculating features...")

            engine = FeatureEngine()

            engine.add_feature(
                "SMA",
                period=20,
            )

            data = engine.calculate(data)

            filepath = features.save_features(data, symbol)

            logger.info(f"{symbol}: Features saved to {filepath}")

        print(data.tail())


if __name__ == "__main__":
    main()
