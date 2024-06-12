import time
import logging
import signal
from typing import List

from stonk_functions import analyze_symbols
from stonk_list import get_symbols, get_good_symbols
from stonk_spreadsheets import update_good_spreadsheets, update_spreadsheet

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants and Configuration
EXCHANGE_LIST = [
    "tsx_{}.txt",
    "xnas_{}.txt",
    "xnyse_{}.txt",
    "cse_{}.txt"
]
RAND_VALUE = 2  # Number of random stocks to analyze
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
    master_list = get_symbols(exchange_list, rand_value=rand_value)
    analyze_symbols(master_list, iter_count)
    
    good_symbols = get_good_symbols()
    update_good_spreadsheets(good_symbols)
    
    okay_symbols = get_good_symbols("okay")
    update_spreadsheet(okay_symbols)
    
    if iter_count == 1 or iter_count % ITERATION_THRESHOLD == 0:
        removed_list = get_symbols(exchange_list, return_bad=True, rand_value=rand_value)
        analyze_symbols(removed_list, iter_count)

def main():
    global shutdown_flag
    iter_count = 1
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while not shutdown_flag:
        try:
            logging.info(f"Starting iteration {iter_count}")
            analyze_and_update(iter_count, RAND_VALUE, EXCHANGE_LIST)
            
            if iter_count > 2:
                logging.info(f"Sleeping for {SLEEP_INTERVAL} seconds.")
                time.sleep(SLEEP_INTERVAL)
            
            iter_count += 1
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            break

if __name__ == "__main__":
    main()
