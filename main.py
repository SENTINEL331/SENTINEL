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

    # ----------------------------------------
    # Configure Feature Engine
    # ----------------------------------------

    engine = FeatureEngine()

    for feature in FEATURE_SET:
        engine.add_feature(
            feature["name"],
            **feature["parameters"],
        )

    # ----------------------------------------
    # Startup Information
    # ----------------------------------------

    show_banner()

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    print()
    print(f"Processing Watchlist ({len(WATCHLIST)} symbols)")
    print()

    ready = 0
    failed = 0

    # ----------------------------------------
    # Process Watchlist
    # ----------------------------------------

    for symbol in WATCHLIST:

        try:

            # ----------------------------
            # History
            # ----------------------------

            history_status = history.get_history_status(symbol)

            if not history_status["exists"]:

                data = manager.download_history(symbol)

                history.save_history(
                    data,
                    symbol,
                )

            data = history.load_history(symbol)

            # ----------------------------
            # Features
            # ----------------------------

            feature_status = features.get_feature_status(symbol)

            if feature_status["exists"]:

                data = features.load_features(symbol)

            else:

                data = engine.calculate(data)

                features.save_features(
                    data,
                    symbol,
                )

            # ----------------------------
            # Display
            # ----------------------------

            show_symbol_summary(symbol)

            ready += 1

        except Exception as error:

            logger.exception(error)
            failed += 1

    # ----------------------------------------
    # Summary
    # ----------------------------------------

    print("=" * 40)
    print("Summary")
    print("=" * 40)

    print(f"Symbols Processed : {len(WATCHLIST)}")
    print(f"Ready             : {ready}")
    print(f"Failed            : {failed}")

    print()
    print("Market Module Complete")


if __name__ == "__main__":
    main()