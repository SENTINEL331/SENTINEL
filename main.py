from market.data_manager import MarketDataManager
from market.history_manager import HistoryManager

from analytics.feature_engine import FeatureEngine
from analytics.feature_store import FeatureStore

from ai.researcher import Researcher
from sentinel.sentinel import Sentinel

from utils.banner import show_banner
from utils.logger import setup_logger

from config.settings import (
    WATCHLIST,
    FEATURE_SET,
)


def main():

    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()
    history = HistoryManager()
    features = FeatureStore()

    #
    # Configure Feature Engine
    #

    engine = FeatureEngine()

    for feature in FEATURE_SET:

        engine.add_feature(
            feature["name"],
            **feature["parameters"],
        )

    #
    # Create Sentinel Interface
    #

    sentinel = Sentinel()

    #
    # Startup
    #

    show_banner()

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    print()
    print(f"Processing Watchlist ({len(WATCHLIST)} symbols)")
    print()

    #
    # Prepare Market Data
    #

    for symbol in WATCHLIST:

        logger.info(f"Processing {symbol}...")

        #
        # History
        #

        history_status = history.get_history_status(symbol)

        if not history_status["exists"]:

            logger.info("Downloading historical data...")

            data = manager.download_history(symbol)

            filepath = history.save_history(
                data,
                symbol,
            )

            logger.info(f"History saved to {filepath}")

        data = history.load_history(symbol)

        #
        # Features
        #

        feature_status = features.get_feature_status(symbol)

        if feature_status["exists"]:

            logger.info("Loading cached features...")

            data = features.load_features(symbol)

        else:

            logger.info("Calculating features...")

            data = engine.calculate(data)

            filepath = features.save_features(
                data,
                symbol,
            )

            logger.info(f"Features saved to {filepath}")

    #
    # AI Research
    #

    researcher = Researcher(sentinel)

    researcher.research()


if __name__ == "__main__":
    main()