from market.market_data import get_status, get_version, get_provider
from utils.banner import show_banner


def main():
    show_banner() 

    print(get_status())
    print(get_version())
    print(f"Data Provider: {get_provider()}")
if __name__ == "__main__":
	main()

