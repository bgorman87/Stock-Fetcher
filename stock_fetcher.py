import logging
import random
from typing import List
import warnings
from database_handler import DatabaseHandler
from stocks_handler import StockFactory, StockData, Stock
from utils import BadStock

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Suppress specific yahooquery FutureWarnings
warnings.filterwarnings("ignore", message=".*'S' is deprecated.*")
warnings.filterwarnings("ignore", message=".*A value is trying to be set on a copy of a DataFrame or Series.*")

EXCHANGE_LIST = ["nas", "nyse", "tsx"]
RAND_VALUE = 0  # Number of random stocks to analyze, mainly used for testing
ITERATION_THRESHOLD = 3

def process_stock(symbol: str, exchange: str, database: DatabaseHandler, stock_set: set):
    """Process and update stock information."""
    try:
        stock = StockFactory.create_stock(symbol, exchange)
        stock_set.add(stock)
        database.update_stock_in_database(stock)
    except BadStock as e:
        logging.error(f"BADSTOCK - {symbol}: {e}")
        bad_stock = StockFactory.create_bad_stock(symbol, exchange)
        database.update_stock_in_database(bad_stock)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        bad_stock = StockFactory.create_bad_stock(symbol, exchange)
        database.update_stock_in_database(bad_stock)

def analyze_and_update(rand_value: int, exchange_list: List[str]):
    """Perform the main analysis and update routine."""
    try:
        database = DatabaseHandler()
    except Exception as e:
        raise e

    stock_set = set()
    logging.info("Fetching existing stocks")
    existing_symbols = database.fetch_existing_symbols()
    for symbol, exchange in existing_symbols:
        stock_data_row = database.fetch_stock_data_from_database(symbol, exchange)
        if not stock_data_row:
            logging.error(f"Stock data not found for {symbol}")
            continue
        stock_data = StockData.from_db_row(stock_data_row)
        stock_set.add(StockFactory.create_stock_from_data(symbol, exchange, stock_data))
    logging.info(f"Found {len(stock_set)} existing stocks")

    new_symbols = database.fetch_new_symbols(exchange_list)

    if rand_value > 0:
        new_symbols = random.sample(list(new_symbols), rand_value)

    # Process new symbols
    for i, (symbol, exchange) in enumerate(new_symbols):
        logging.info(
            f"Processing new stock {symbol} - {exchange} : {i + 1}/{len(new_symbols)}"
        )
        process_stock(symbol, exchange, database, stock_set)

    # Update existing stocks in order of quality
    for i, stock in enumerate(sorted(list(stock_set))):
        assert isinstance(stock, Stock)
        logging.info(
            f"Processing existing stock {stock.symbol} - {stock.exchange} : {i + 1}/{len(existing_symbols)}"
        )
        process_stock(stock.symbol, stock.exchange, database, stock_set)

if __name__ == "__main__":
    try:
        logging.info("Starting processing")
        analyze_and_update(RAND_VALUE, EXCHANGE_LIST)
    except Exception as e:
        logging.error(f"Fatal error occurred: {e}")
