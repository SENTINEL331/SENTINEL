from market.data_manager import MarketDataManager 
from utils.banner import show_banner
from utils.logger import setup_logger
from config.settings import WATCHLIST
from market.history_manager import HistoryManager
from analytics.feature_engine import FeatureEngine

def main():
    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()
    history = HistoryManager()

    show_banner() 

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    for symbol in WATCHLIST:

        status = history.get_history_status(symbol)

        logger.info(f"{symbol}: {status}")

        if status["exists"]:

            logger.info(f"{symbol}: Latest data = {status['latest_date'].date()}")
            logger.info(f"{symbol}: Existing data found. Skipping download.")

            data = history.load_history(symbol)

            engine = FeatureEngine()

            engine.add_feature(
                "SMA",
                period=20
            )

            data = engine.calculate(data)

            print(data.tail())

            continue

        logger.info(f"{symbol}: No data found.")
        logger.info(f"Downloading {symbol}...")

        data = manager.download_history(symbol)

        filepath = history.save_history(data, symbol)

        logger.info(f"Data saved to {filepath}")

if __name__ == "__main__":
      main()

