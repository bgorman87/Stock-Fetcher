import logging
import signal
import time
import random
from typing import List

from database_handler import DatabaseHandler
from stonks import StockFactory, StockData
from utils import BadStock

# from stonk_spreadsheets import update_good_spreadsheets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

EXCHANGE_LIST = ["tsx", "nas", "nyse", "cse"]
EXCHANGE_LIST = ["nas"]
RAND_VALUE = 0  # Number of random stocks to analyze
SLEEP_INTERVAL = 43200 / 2  # 12 hours divided by 2
ITERATION_THRESHOLD = 3

# Graceful shutdown flag
shutdown_flag = False


def signal_handler(sig, frame):
    global shutdown_flag
    logging.info("Shutdown signal received, stopping the program.")
    shutdown_flag = True


def analyze_and_update(iter_count: int, rand_value: int, exchange_list: List[str]):
    """Perform the main analysis and update routine."""
    database = DatabaseHandler()

    stock_set = set()
    # existing_symbols = database.fetch_existing_symbols()
    # for symbol, exchange in existing_symbols:
    #     stock_data = database.fetch_stock_data_from_database(symbol, exchange)
    #     if not stock_data:
    #         logging.error(f"Stock data not found for {symbol}")
    #         continue
    #     stock_data = StockData(*stock_data[2:])
    #     stock_set.add(StockFactory.create_stock_from_data(symbol, exchange, stock_data))

    new_symbols = database.fetch_new_symbols(exchange_list)
    if rand_value > 0:
        new_symbols = random.sample(list(new_symbols), rand_value)
    for i, (symbol, exchange) in enumerate(new_symbols):
        logging.info(f"Fetching data for {symbol} - {exchange} : {i + 1}/{len(new_symbols)}")
        try:
            stock = StockFactory.create_stock(symbol, exchange)
            stock_set.add(stock)
            print(stock)
            print(stock.get_summary())
            database.update_stock_in_database(stock)
        except BadStock as e:
            logging.error(f"BADSTOCK - {symbol}: {e}")
            database.set_invalid_symbol(symbol, exchange)
            continue
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            continue
    return

    # good_stocks = get_stocks_from_quality(quality=StockQuality.GOOD)
    # update_good_spreadsheets(good_stocks)

    # okay_symbols = get_good_symbols("okay")
    # update_spreadsheet(okay_symbols)

    # if iter_count == 1 or iter_count % ITERATION_THRESHOLD == 0:
    #     removed_list = get_symbols(exchange_list, return_bad=True, rand_value=rand_value)
    #     analyze_symbols(removed_list, iter_count)


def main():
    global shutdown_flag
    iter_count = 0
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # while not shutdown_flag:
    try:
        logging.info(f"Starting iteration {iter_count}")
        analyze_and_update(iter_count, RAND_VALUE, EXCHANGE_LIST)

        if iter_count > 0:
            logging.info(f"Sleeping for {SLEEP_INTERVAL} seconds.")
            # time.sleep(SLEEP_INTERVAL)

        iter_count += 1
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # break


if __name__ == "__main__":
    main()
