import logging
import time
import sqlite3
import os
import random
from contextlib import contextmanager
from typing import Generator
from stonks import Stock, StockQuality

from utils import ExistingStock, RecentlyUpdated


class DatabaseHandler:
    DB_FILE_PATH = os.getenv("DB_FILE_PATH", "sqlite/stonks.db")
    EXCHANGE_FILES_DIRECTORY = os.getenv(
        "EXCHANGE_FILES_DIRECTORY", "Stonks Files/Input/"
    )

    def __init__(self, db_file_path: str = DB_FILE_PATH):
        self.db_file_path = db_file_path
        self.initialize_database()

    @contextmanager
    def connect_to_database(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for SQLite database connection."""
        conn = sqlite3.connect(self.db_file_path)
        try:
            yield conn
        finally:
            conn.close()

    def initialize_database(self) -> None:
        """Initialize the SQLite database."""
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.execute("""CREATE TABLE IF NOT EXISTS stonks(
                    symbol TEXT PRIMARY KEY, exchange TEXT, current REAL, pe REAL, dcf REAL,  
                    roe REAL, quality INTEGER, title TEXT, industry TEXT, market_cap REAL, 
                    revenue REAL, net_income REAL, assets REAL, liabilities REAL, debt REAL, 
                    esg_score REAL, controversy REAL, summary TEXT, long_term_debt REAL, growth_estimate REAL, 
                    current_eps REAL, historical_pe REAL, cash_raw_eq REAL, fcf_raw_value REAL,
                    shares_outstanding_raw REAL, stockholders_equity_raw REAL, historical_roe REAL,
                    trailing_dividend_rate_raw REAL, last_updated TEXT)""")
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS symbols(symbol TEXT PRIMARY KEY, exchange TEXT, 
                    valid INTEGER DEFAULT 1, last_updated TEXT DEFAULT CURRENT_TIMESTAMP)"""
                )
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database initialization failed: {e}")

    def read_symbols_from_files(self, file_paths: list[str]) -> list[tuple[str, str]]:
        """Read symbols from exchange files."""
        symbols = []
        for exchange in file_paths:
            full_path = os.path.join(self.EXCHANGE_FILES_DIRECTORY, f"{exchange}.txt")
            with open(full_path, "r") as file:
                symbols.extend(
                    [(line.strip(), exchange) for line in file if line.strip()]
                )
        return symbols

    def update_symbols_from_files(self, file_paths: list[str]) -> None:
        """Update the symbols in the database from exchange files."""
        all_symbols = self.read_symbols_from_files(file_paths)
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.executemany(
                    """INSERT OR IGNORE INTO symbols(symbol, exchange) VALUES(?, ?)""",
                    all_symbols,
                )
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error updating symbols: {e}")

    def fetch_new_symbols(self, local_exchange_list: list[str]) -> set[tuple[str, str]]:
        """Get new symbols from the exchange files."""
        all_symbols = set(self.fetch_all_symbols(local_exchange_list))
        query = """SELECT symbol, exchange FROM stonks"""
        try:
            results = self.execute_query(query, ())
            existing_symbols = set([(row[0], row[1]) for row in results])
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            existing_symbols = set()

        new_symbols = all_symbols - existing_symbols
        return new_symbols

    def fetch_existing_symbols(self) -> set[tuple[str, str]]:
        """Get existing symbols from the exchange files."""
        query = """SELECT symbol, exchange FROM stonks"""
        try:
            results = self.execute_query(query, ())
            existing_symbols = set([(row[0], row[1]) for row in results])
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            existing_symbols = set()

        existing_symbols = existing_symbols
        return existing_symbols

    def fetch_all_symbols(
        self,
        local_exchange_list: list[str],
        rand_value: int = 0,
        quality: StockQuality = StockQuality.BAD,
    ) -> list[tuple[str, str]]:
        """Fetch all symbols from the database and exchange files.

        Args:
            local_exchange_list (list[str]): List of exchanges being used.
            rand_value (int, optional): Length of list to return. Defaults to 0, which returns all symbols.
            quality (StockQuality, optional): Minimum quality of stock to return. Defaults to StockQuality.BAD.

        Returns:
            list[tuple[str, str]]: List of symbol, exchange tuples.
        """
        try:
            self.update_symbols_from_files(local_exchange_list)
            query = "SELECT symbol, exchange FROM symbols WHERE valid=1"
            try:
                results = self.execute_query(query, ())
                all_symbols = [(row[0], row[1]) for row in results]
            except Exception as e:
                logging.error(f"Error fetching symbols: {e}")
                all_symbols = []

            master_list = set(self.get_better_quality_stocks(quality=quality)) | set(
                all_symbols
            )

            if rand_value > 0:
                master_list = random.sample(
                    master_list, min(rand_value, len(master_list))
                )

            logging.info(f"Master List is {len(master_list)} symbols")
            return master_list
        except Exception as e:
            logging.error(f"Error getting symbols: {e}")
            return []

    def execute_query(self, query: str, params: tuple) -> list[tuple]:
        """Execute a query and return the results if any."""
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database query failed: {e}")
            return None

    def get_better_quality_stocks(
        self, quality: StockQuality = StockQuality.OKAY
    ) -> list[tuple[str, str]]:
        """Get good symbols from the database based on quality."""
        query = "SELECT symbol, exchange FROM stonks WHERE quality < ?"
        try:
            results = self.execute_query(query, (quality.value,))
            return [(row[0], row[1]) for row in results]
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            return []

    def get_worse_quality_stocks(
        self, quality: StockQuality = StockQuality.OKAY
    ) -> list[tuple[str, str]]:
        """Get good symbols from the database based on quality."""
        query = "SELECT symbol, exchange FROM stonks WHERE quality > ?"
        try:
            results = self.execute_query(query, (quality.value,))
            return [(row[0], row[1]) for row in results]
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            return []

    def check_existing_stock(self, symbol: str):
        """Check if the stock already exists in the database."""
        query = "SELECT 1 FROM stonks WHERE symbol=?"
        try:
            result = self.execute_query(query, (symbol,))
            if result:
                raise ExistingStock(f"Stock {symbol} already exists.")
        except Exception as e:
            logging.error(f"Error checking existing stock: {e}")

    def check_recent_update(self, symbol: str):
        """Check if the stock was recently updated."""
        query = "SELECT last_updated FROM stonks WHERE symbol=?"
        try:
            result = self.execute_query(query, (symbol,))
            if result and time.time() - result[0] < 43200:  # 12 hours in seconds
                raise RecentlyUpdated(f"Stock {symbol} was recently updated.")
        except Exception as e:
            logging.error(f"Error checking recent update: {e}")

    def fetch_stock_data_from_database(self, symbol: str, exchange: str) -> Stock:
        """Fetch a stock from the database."""
        query = "SELECT * FROM stonks WHERE symbol=? AND exchange=?"
        try:
            result = self.execute_query(query, (symbol, exchange))
            if result:
                return result[0]
            return None
        except Exception as e:
            logging.error(f"Error fetching stock: {e}")

    def update_stock_in_database(self, stock: Stock) -> bool:
        """Update or insert stonk in the database."""

        values = tuple(
            [
                stock.stock_data.current_price,
                stock.stock_data.pe,
                stock.stock_data.dcf,
                stock.stock_data.roe,
                stock.exchange,
                stock.stock_data.quality.value,
                stock.stock_data.title,
                stock.stock_data.industry,
                stock.stock_data.market_cap,
                stock.stock_data.revenue,
                stock.stock_data.net_income,
                stock.stock_data.assets,
                stock.stock_data.liabilities,
                stock.stock_data.debt,
                stock.stock_data.esg_score,
                stock.stock_data.controversy,
                stock.stock_data.summary,
                stock.stock_data.last_updated,
                stock.stock_data.long_term_debt,
                stock.stock_data.growth_estimate,
                stock.stock_data.current_eps,
                stock.stock_data.historical_pe,
                stock.stock_data.cash_raw_eq,
                stock.stock_data.fcf_raw_value,
                stock.stock_data.shares_outstanding_raw,
                stock.stock_data.stockholders_equity_raw,
                stock.stock_data.historical_roe,
                stock.stock_data.trailing_dividend_rate_raw,
                stock.symbol,
            ]
        )
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                if cur.execute(
                    "SELECT 1 FROM stonks WHERE symbol=? AND exchange=?",
                    (
                        stock.symbol,
                        stock.exchange,
                    ),
                ).fetchone():
                    cur.execute(
                        """UPDATE stonks SET 
                        current=?, pe=?, dcf=?, roe=?, exchange=?, quality=?, title=?, industry=?,
                        market_cap=?, revenue=?, net_income=?, assets=?, liabilities=?, debt=?,
                        esg_score=?, controversy=?, summary=?, last_updated=?, long_term_debt=?,
                        growth_estimate=?, current_eps=?, historical_pe=?, cash_raw_eq=?, fcf_raw_value=?,
                        shares_outstanding_raw=?, stockholders_equity_raw=?, historical_roe=?,
                        trailing_dividend_rate_raw=? WHERE symbol=?""",
                        values,
                    )
                else:
                    cur.execute(
                        """INSERT INTO stonks(
                        current, pe, dcf, roe, exchange, quality, title, industry, market_cap,
                        revenue, net_income, assets, liabilities, debt, esg_score, controversy,
                        summary, last_updated, long_term_debt, growth_estimate, current_eps,
                        historical_pe, cash_raw_eq, fcf_raw_value, shares_outstanding_raw,
                        stockholders_equity_raw, historical_roe, trailing_dividend_rate_raw, symbol
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        values,
                    )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database update failed: {e}")
            return False
        
    def set_invalid_symbol(self, symbol: str, exchange: str) -> None:
        """Set a symbol as invalid in the database."""
        query = "UPDATE symbols SET valid=0 WHERE symbol=? AND exchange=?"
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.execute(query, (symbol, exchange))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error setting invalid symbol: {e}")
            return None
