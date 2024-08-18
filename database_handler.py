import logging
import os
import os
import random
import psycopg2

from psycopg2.extras import DictCursor
from contextlib import contextmanager
from typing import Generator

from stocks_handler import Stock, StockQuality
from utils import ExistingStock


class DatabaseHandler:
    DB_HOST = os.getenv("DATABASE_HOST", "localhost")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    DB_NAME = os.getenv("DATABASE_NAME", "database")
    DB_USER = os.getenv("DATABASE_USER", "postgres")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
    EXCHANGE_FILES_DIRECTORY = os.getenv("EXCHANGE_FILES_DIRECTORY", "Symbol Files")

    def __init__(self):
        self.connection_string = self.create_connection_string()
        self.test_connection()

    def create_connection_string(self) -> str:
        return f"host={self.DB_HOST} port={self.DB_PORT} dbname={self.DB_NAME} user={self.DB_USER} password={self.DB_PASSWORD}"

    def test_connection(self) -> None:
        """Test the connection to the PostgreSQL database."""
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                logging.info("Successfully connected to the database.")
        except psycopg2.Error as e:
            logging.error(f"Error connecting to the database")
            raise e

    @contextmanager
    def connect_to_database(
        self,
    ) -> Generator[psycopg2.extensions.connection, None, None]:
        """Context manager for PostgreSQL database connection."""
        conn = psycopg2.connect(self.connection_string, cursor_factory=DictCursor)
        try:
            yield conn
        finally:
            conn.close()

    def read_symbols_from_files(self, file_paths: list[str]) -> list[tuple[str, str]]:
        """Read symbols from exchange files."""
        symbols = []

        if not os.path.exists(self.EXCHANGE_FILES_DIRECTORY):
            raise FileNotFoundError(
                f"Directory {self.EXCHANGE_FILES_DIRECTORY} not found."
            )

        for exchange in file_paths:
            full_path = os.path.join(self.EXCHANGE_FILES_DIRECTORY, f"{exchange}.txt")

            try:
                with open(full_path, "r") as file:
                    symbols.extend(
                        [(line.strip(), exchange) for line in file if line.strip()]
                    )
            except FileNotFoundError:
                logging.error(f"File {full_path} not found.")
            except IOError as e:
                logging.error(f"Error reading file {full_path}: {e}")

        return symbols

    def update_stock_symbols_from_files(self, file_paths: list[str]) -> None:
        """Update the stocks table with symbols from exchange files."""
        all_symbols = self.read_symbols_from_files(file_paths)

        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.executemany(
                    """INSERT INTO stocks(symbol, exchange) 
                    VALUES(%s, %s) 
                    ON CONFLICT(symbol, exchange) DO NOTHING""",
                    all_symbols,
                )
                conn.commit()
                logging.info(
                    f"Successfully updated {cur.rowcount} stocks in the database."
                )
        except psycopg2.Error as e:
            conn.rollback()
            logging.error(f"Error updating stocks: {e}")
        finally:
            if cur:
                cur.close()

    def fetch_new_symbols(self, local_exchange_list: list[str]) -> set[tuple[str, str]]:
        """Get new symbols from the exchange files."""
        all_symbols = set(self.read_symbols_from_files(local_exchange_list))
        query = """SELECT symbol, exchange FROM stocks"""

        try:
            results = self.execute_query(query, ())
            existing_symbols = set((row[0], row[1]) for row in results)
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            existing_symbols = set()

        new_symbols = all_symbols - existing_symbols
        return new_symbols

    def fetch_existing_symbols(self) -> set[tuple[str, str]]:
        """Get existing symbols from the stocks table."""
        query = """SELECT symbol, exchange FROM stocks"""

        try:
            results = self.execute_query(query, ())
            existing_symbols = set((row[0], row[1]) for row in results)
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            existing_symbols = set()

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
            self.update_stock_symbols_from_files(local_exchange_list)

            query = """
                SELECT symbol, exchange 
                FROM stocks 
                WHERE quality >= %s
            """
            try:
                results = self.execute_query(query, (quality.value,))
                all_symbols = [(row["symbol"], row["exchange"]) for row in results]
            except Exception as e:
                logging.error(f"Error fetching symbols: {e}")
                all_symbols = []

            master_list = set(all_symbols)

            if rand_value > 0:
                master_list = random.sample(
                    master_list, min(rand_value, len(master_list))
                )

            logging.info(f"Master List is {len(master_list)} symbols")
            return list(master_list)
        except Exception as e:
            logging.error(f"Error getting symbols: {e}")
            return []

    def execute_query(
        self, query: str, params: tuple = (), fetchone=False
    ) -> list[dict] | dict | None:
        """Execute a query and return the results as a list of dictionaries if any."""
        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor(cursor_factory=DictCursor)
                cur.execute(query, params)
                if fetchone:
                    return cur.fetchone()
                return cur.fetchall()
        except psycopg2.Error as e:
            logging.error(f"Database query failed: {e}")
            return None

    def get_better_quality_stocks(
        self, quality: StockQuality = StockQuality.OKAY
    ) -> list[tuple[str, str]]:
        """Get good symbols from the database based on quality.

        Args:
            quality (StockQuality, optional): Maximum quality of stock to return. Defaults to StockQuality.OKAY.

        Returns:
            list[tuple[str, str]]: List of symbol, exchange tuples with quality better than the specified level.
        """
        query = "SELECT symbol, exchange FROM stocks WHERE quality <= %s"
        try:
            results = self.execute_query(query, (quality.value,))
            return [(row["symbol"], row["exchange"]) for row in results]
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            return []

    def get_worse_quality_stocks(
        self, quality: StockQuality = StockQuality.OKAY
    ) -> list[tuple[str, str]]:
        """Get symbols from the database that have worse quality than the specified level.

        Args:
            quality (StockQuality, optional): Minimum quality of stock to return. Defaults to StockQuality.OKAY.

        Returns:
            list[tuple[str, str]]: List of symbol, exchange tuples with quality worse than the specified level.
        """
        query = "SELECT symbol, exchange FROM stocks WHERE quality > %s"
        try:
            results = self.execute_query(query, (quality.value,))
            return [(row["symbol"], row["exchange"]) for row in results]
        except Exception as e:
            logging.error(f"Error fetching symbols: {e}")
            return []

    def check_existing_stock(self, symbol: str) -> bool:
        """Check if the stock already exists in the database.

        Args:
            symbol (str): The stock symbol to check.

        Returns:
            bool: True if the stock exists, False otherwise.

        Raises:
            ExistingStock: If the stock exists in the database.
        """
        query = "SELECT 1 FROM stocks WHERE symbol=%s LIMIT 1"
        try:
            result = self.execute_query(query, (symbol,))
            if result:
                raise ExistingStock(f"Stock {symbol} already exists.")
            return False
        except ExistingStock:
            raise
        except Exception as e:
            logging.error(f"Error checking existing stock: {e}")
            return False

    def fetch_stock_data_from_database(self, symbol: str, exchange: str) -> tuple:
        """Fetch a stock from the database by symbol and exchange.

        Args:
            symbol (str): The stock symbol to fetch.
            exchange (str): The exchange where the stock is listed.

        Returns:
            tuple: A tuple containing all the fields of the stock record if found, or None if not found.
        """
        query = "SELECT * FROM stocks WHERE symbol=%s AND exchange=%s"
        try:
            result = self.execute_query(query, (symbol, exchange), fetchone=True)
            if result:
                return result
            return None
        except Exception as e:
            logging.error(f"Error fetching stock: {e}")
            return None

    def update_stock_in_database(self, stock: Stock) -> bool:
        """Update or insert stock in the database."""

        values = (
            stock.stock_data.current_price,
            stock.stock_data.pe,
            stock.stock_data.dcf,
            stock.stock_data.roe,
            stock.exchange,
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
        )

        try:
            with self.connect_to_database() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM stocks WHERE symbol=%s AND exchange=%s",
                    (stock.symbol, stock.exchange),
                )
                stock_row = cur.fetchone()

                if stock_row:
                    stock_id = stock_row[0]
                    cur.execute(
                        """UPDATE stocks SET 
                        current=%s, pe=%s, dcf=%s, roe=%s, exchange=%s, title=%s, industry=%s,
                        marketcap=%s, revenue=%s, netincome=%s, assets=%s, liabilities=%s, debt=%s,
                        esgscore=%s, controversy=%s, summary=%s, longtermdebt=%s,
                        growthestimate=%s, currenteps=%s, historicalpe=%s, cashraweq=%s, fcfrawvalue=%s,
                        sharesoutstandingraw=%s, stockholdersequityraw=%s, historicalroe=%s,
                        trailingdividendrateraw=%s WHERE symbol=%s AND exchange=%s""",
                        values + (stock.exchange,),
                    )
                    conn.commit()
                else:
                    cur.execute(
                        """INSERT INTO stocks(
                        current, pe, dcf, roe, exchange, title, industry, marketcap,
                        revenue, netincome, assets, liabilities, debt, esgscore, controversy,
                        summary, longtermdebt, growthestimate, currenteps,
                        historicalpe, cashraweq, fcfrawvalue, sharesoutstandingraw,
                        stockholdersequityraw, historicalroe, trailingdividendrateraw, symbol
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        values,
                    )
                    cur.execute(
                        "SELECT id FROM stocks WHERE symbol=%s AND exchange=%s",
                        (stock.symbol, stock.exchange),
                    )
                    conn.commit()
                    stock_id = cur.fetchone()[0]

                if stock.stock_data.news:
                    for news_item in stock.stock_data.news:
                        cur.execute(
                            """INSERT INTO news(
                            stock_id, news_id, title, summary, url, provider_name, provider_publish_time
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (news_id) DO NOTHING""",
                            (
                                stock_id,
                                news_item.id,
                                news_item.title,
                                news_item.summary,
                                news_item.url,
                                news_item.provider_name,
                                news_item.provider_publish_time,
                            ),
                        )
                    conn.commit()
            return True
        except psycopg2.Error as e:
            logging.error(f"Database update failed: {e}")
            return False
