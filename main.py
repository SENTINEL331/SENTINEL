from market.data_manager import MarketDataManager 
from utils.banner import show_banner
from utils.logger import setup_logger

def main():
    logger = setup_logger()
    logger.info("Sentinel is starting...")

    manager = MarketDataManager()

    show_banner() 

    print(manager.get_status())
    print(manager.get_version())
    print(f"Data Provider: {manager.get_provider()}")
if __name__ == "__main__":
	main()

