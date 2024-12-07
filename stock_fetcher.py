import logging
import random
import warnings
import time
import os
from logging.handlers import RotatingFileHandler
from database_handler import DatabaseHandler
from stocks_handler import StockFactory
from utils import BadStock

# Log directory setup
log_dir = os.getenv("LOG_DIR", "/var/log/stock-fetcher/")
try:
    if not os.path.exists(log_dir):
        log_dir = os.getenv("FALLBACK_LOG_DIR", "logs/")
        os.makedirs(log_dir, exist_ok=True)
except OSError as e:
    print(f"Failed to create log directory {log_dir}: {e}")
    log_dir = "logs/"
    os.makedirs(log_dir, exist_ok=True)

# File handler with rotation
log_file = os.path.join(log_dir, "stock-fetcher.log")
log_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,  # Keep 5 backups
)

# Log level from environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log_handler.setFormatter(formatter)

# Stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Root logger configuration
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level, logging.INFO))
root_logger.addHandler(log_handler)
root_logger.addHandler(stream_handler)


logger = logging.getLogger(__name__)


# Suppress specific yahooquery FutureWarnings
warnings.filterwarnings("ignore", message=".*'S' is deprecated.*")
warnings.filterwarnings(
    "ignore",
    message=".*A value is trying to be set on a copy of a DataFrame or Series.*",
)

EXCHANGE_LIST = ["nas", "nyse", "tsx"]
RAND_VALUE = 0  # Number of random stocks to analyze, mainly used for testing


def process_stock(symbol: str, exchange: str, database: DatabaseHandler):
    """Process and update stock information."""
    try:
        stock = StockFactory.create_stock(symbol, exchange)
        database.update_stock_in_database(stock)
    except BadStock as e:
        logger.error(f"BADSTOCK - {symbol}: {e.message}")
        bad_stock = StockFactory.create_stock_from_data(symbol, exchange, e.stock_data)
        database.update_stock_in_database(bad_stock)
        pass
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        # bad_stock = StockFactory.create_stock_from_data(symbol, exchange, StockData())
        # database.update_stock_in_database(bad_stock)
        pass


def analyze_and_update(rand_value: int, exchange_list: list[str]):
    """Perform the main analysis and update routine."""
    try:
        database = DatabaseHandler()
    except Exception as e:
        raise e

    new_symbols = database.fetch_new_symbols(exchange_list)

    if rand_value > 0:
        new_symbols = random.sample(list(new_symbols), rand_value)

    # Process new symbols first
    for i, (symbol, exchange) in enumerate(new_symbols):
        logger.info(
            f"Processing new stock {symbol} - {exchange} : {i + 1}/{len(new_symbols)}"
        )
        process_stock(symbol, exchange, database)

    #Process existing symbols next
    logger.info("Fetching existing stocks")
    existing_symbols = database.fetch_existing_symbols()
    for i, (symbol, exchange) in enumerate(list(existing_symbols)):
        logger.info(
            f"Processing existing stock {symbol} - {exchange} : {i + 1}/{len(existing_symbols)}"
        )

        # TODO: Implement database check for last_updated rather than initializing every stock
        # if (time.time() - stock.stock_data.last_updated) < (60 * 60 * 12):  # 12 hours
        #     logger.info(f"Stock {stock.symbol} was recently updated")
        #     continue

        process_stock(symbol, exchange, database)

if __name__ == "__main__":
    
    try:
        logger.info("Starting processing")
        analyze_and_update(RAND_VALUE, EXCHANGE_LIST)
    except Exception as e:
        logger.error(f"Fatal error occurred: {e}")
