from market.data_manager import MarketDataManager
from market.history_manager import HistoryManager

from analytics.feature_engine import FeatureEngine
from analytics.feature_store import FeatureStore

from utils.banner import show_banner
from utils.display import show_symbol_summary
from utils.logger import setup_logger

from config.settings import WATCHLIST, FEATURE_SET


def main():
    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()
    history = HistoryManager()
    features = FeatureStore()

    # Configure Feature Engine
    engine = FeatureEngine()

    for feature in FEATURE_SET:
        engine.add_feature(
            feature["name"],
            **feature["parameters"],
        )

    # Display startup information
    show_banner()

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    # Process each symbol
    for symbol in WATCHLIST:

        logger.info(f"Processing {symbol}...")

        # ----------------------------------------
        # History
        # ----------------------------------------

        history_status = history.get_history_status(symbol)

        if not history_status["exists"]:

            logger.info("Downloading historical data...")

            data = manager.download_history(symbol)

            filepath = history.save_history(data, symbol)

            logger.info(f"History saved to {filepath}")

        # Load history
        data = history.load_history(symbol)

        # ----------------------------------------
        # Features
        # ----------------------------------------

        feature_status = features.get_feature_status(symbol)

        if feature_status["exists"]:

            logger.info("Loading cached features...")

            data = features.load_features(symbol)

        else:

            logger.info("Calculating features...")

            data = engine.calculate(data)

            filepath = features.save_features(data, symbol)

            logger.info(f"Features saved to {filepath}")

        # ----------------------------------------
        # Display Summary
        # ----------------------------------------

        show_symbol_summary(
            symbol,
            data,
        )


if __name__ == "__main__":
    main()