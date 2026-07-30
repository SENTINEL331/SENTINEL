import logging
from pathlib import Path


def setup_logger():
    """Configure and return the Sentinel logger."""

    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_directory / "sentinel.log"),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger("Sentinel")
