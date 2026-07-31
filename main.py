from market.data_manager import MarketDataManager 
from utils.banner import show_banner
from utils.logger import setup_logger
from config.settings import WATCHLIST

def main():
    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()

    show_banner() 

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")

    for symbol in WATCHLIST:
        logger.info(f"Downloading {symbol}...")

        data = manager.download_history(symbol)

        filepath = manager.save_history(data, symbol)

        logger.info(f"Data saved to {filepath}")

if __name__ == "__main__":
      main()

