import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ExistingStock(Exception):
    """Exception raised when a stock already exists in the database."""

    def __init__(self, message="The stock already exists in the database"):
        super().__init__(message)


class BadStock(Exception):
    """Exception raised when a stock is bad."""

    def __init__(self, stock_data, message="There was an error with the stock"):
        super().__init__(message)
        self.stock_data = stock_data
        self.message = message


class RecentlyUpdated(Exception):
    """Exception raised when a stock was recently updated."""

    def __init__(self, message="The stock was recently updated"):
        super().__init__(message)
