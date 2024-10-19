import logging
import random
import warnings
import time
import os
from logging.handlers import RotatingFileHandler
from database_handler import DatabaseHandler
from stocks_handler import StockFactory, StockData
from utils import BadStock


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
        logging.error(f"BADSTOCK - {symbol}: {e.message}")
        bad_stock = StockFactory.create_stock_from_data(symbol, exchange, e.stock_data)
        database.update_stock_in_database(bad_stock)
        pass
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        bad_stock = StockFactory.create_stock_from_data(symbol, exchange, StockData())
        database.update_stock_in_database(bad_stock)
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
        logging.info(
            f"Processing new stock {symbol} - {exchange} : {i + 1}/{len(new_symbols)}"
        )
        process_stock(symbol, exchange, database)

    # Process existing symbols next
    logging.info("Fetching existing stocks")
    existing_symbols = database.fetch_existing_symbols()
    for i, (symbol, exchange) in enumerate(list(existing_symbols)):
        logging.info(
            f"Processing existing stock {symbol} - {exchange} : {i + 1}/{len(existing_symbols)}"
        )

        # TODO: Implement database check for last_updated rather than initializing every stock
        # if (time.time() - stock.stock_data.last_updated) < (60 * 60 * 12):  # 12 hours
        #     logging.info(f"Stock {stock.symbol} was recently updated")
        #     continue

        process_stock(symbol, exchange, database)

if __name__ == "__main__":
    log_dir = os.path.abspath("/var/log/stock-fetcher/")
    if not os.path.exists(log_dir):
        log_dir = os.path.abspath("logs/")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    log_handler = RotatingFileHandler(
        os.path.join(log_dir, "stock-fetcher.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB per file
        backupCount=5,
    )

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)
    root_logger.addHandler(logging.StreamHandler())

    try:
        logging.info("Starting processing")
        analyze_and_update(RAND_VALUE, EXCHANGE_LIST)
    except Exception as e:
        logging.error(f"Fatal error occurred: {e}")
