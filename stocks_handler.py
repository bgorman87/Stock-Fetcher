from dataclasses import dataclass, fields
from enum import Enum
import pandas as pd
import time
import logging
import yahooquery
from utils import BadStock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class StockQuality(Enum):
    GOOD = 1
    OKAY = 2
    BAD = 3
    UNKNOWN = 4


@dataclass
class StockData:
    current_price: float
    pe: float
    dcf: float
    roe: float
    quality: StockQuality
    title: str
    industry: str
    market_cap: float
    revenue: float
    net_income: float
    assets: float
    liabilities: float
    debt: float
    esg_score: float
    controversy: float
    summary: str
    long_term_debt: float
    growth_estimate: float
    current_eps: float
    historical_pe: float
    cash_raw_eq: float
    fcf_raw_value: float
    shares_outstanding_raw: float
    stockholders_equity_raw: float
    historical_roe: float
    trailing_dividend_rate_raw: float
    last_updated: int

    @staticmethod
    def from_db_row(row: dict) -> "StockData":
        """Factory method to create StockData from a database row dictionary."""
        return StockData(
            current_price=row["current"],
            pe=row["pe"],
            dcf=row["dcf"],
            roe=row["roe"],
            quality=StockQuality(row["quality"]),
            title=row["title"],
            industry=row["industry"],
            market_cap=row["marketcap"],
            revenue=row["revenue"],
            net_income=row["netincome"],
            assets=row["assets"],
            liabilities=row["liabilities"],
            debt=row["debt"],
            esg_score=row["esgscore"],
            controversy=row["controversy"],
            summary=row["summary"],
            long_term_debt=row["longtermdebt"],
            growth_estimate=row["growthestimate"],
            current_eps=row["currenteps"],
            historical_pe=row["historicalpe"],
            cash_raw_eq=row["cashraweq"],
            fcf_raw_value=row["fcfrawvalue"],
            shares_outstanding_raw=row["sharesoutstandingraw"],
            stockholders_equity_raw=row["stockholdersequityraw"],
            historical_roe=row["historicalroe"],
            trailing_dividend_rate_raw=row["trailingdividendrateraw"],
            last_updated=row["lastupdated"].timestamp(),  # Convert to Unix timestamp
        )


class Stock:
    def __init__(self, symbol: str, exchange: str, stock_data: StockData):
        self.symbol: str = symbol
        self.exchange: str = exchange
        self.stock_data: StockData = stock_data

    def __str__(self):
        return f"{self.symbol} - {self.exchange} - {self.stock_data.title}".upper()

    def __repr__(self):
        return f"{self.symbol} - {self.exchange} - {self.stock_data.title}".upper()

    def __eq__(self, other: "Stock"):
        return self.symbol == other.symbol and self.exchange == other.exchange

    def __hash__(self) -> int:
        return hash((self.symbol, self.exchange))
    
    def __lt__(self, other: "Stock"):
        # This will sort in ascending order (1 is higher quality than 4)
        return self.stock_data.quality.value < other.stock_data.quality.value

    def get_summary(self):
        return f"${self.stock_data.current_price:.2f} - {self.stock_data.quality.name} - PE: ${self.stock_data.pe:.2f} DCF: ${self.stock_data.dcf:.2f} ROE: ${self.stock_data.roe:.2f}"


class StockFactory:
    DISCOUNT_RATE = 0.09

    key_paths = {
        "MarketCap": ["summaryDetail", "marketCap"],
        "TotalRevenue": [
            "incomeStatementHistory",
            "incomeStatementHistory",
            0,
            "totalRevenue",
        ],
        "NetIncome": [
            "incomeStatementHistory",
            "incomeStatementHistory",
            0,
            "netIncome",
        ],
        "TotalAssets": [
            "balanceSheetHistoryQuarterly",
            "balanceSheetStatements",
            0,
            "totalAssets",
        ],
        "TotalLiabilitiesNetMinorityInterest": [
            "balanceSheetHistory",
            "balanceSheetStatements",
            0,
            "totalLiab",
        ],
        "TotalDebt": ["financialData", "totalDebt"],
        "ReturnOnEquity": ["financialData", "returnOnEquity"],
        "LongTermDebt": [
            "balanceSheetHistoryQuarterly",
            "balanceSheetStatements",
            0,
            "longTermDebt",
        ],
        "CashAndCashEquivalents": [
            "balanceSheetHistory",
            "balanceSheetStatements",
            0,
            "cash",
        ],
        "StockholdersEquity": [
            "balanceSheetHistory",
            "balanceSheetStatements",
            0,
            "totalStockholderEquity",
        ],
    }

    @staticmethod
    def validate_growth_estimate(stock: Stock):
        """Validate the growth estimate of the stock."""
        if not isinstance(stock.stock_data.growth_estimate, (int, float)):
            stock.stock_data.growth_estimate = 0

    @staticmethod
    def determine_and_update_stock_quality(stock: Stock):
        """Determine the quality of the stock based on calculated values."""
        try:
            good_values = [
                value
                for value in [
                    stock.stock_data.pe,
                    stock.stock_data.dcf,
                    stock.stock_data.roe,
                ]
                if stock.stock_data.current_price < value
            ]
            if len(good_values) == 3:
                stock.stock_data.quality = StockQuality.GOOD
            elif len(good_values) == 2:
                stock.stock_data.quality = StockQuality.OKAY
            else:
                stock.stock_data.quality = StockQuality.BAD
        except Exception:
            stock.stock_data.quality = StockQuality.BAD

    @staticmethod
    def calculate_pe_npv(discount_rate: float, stock: Stock) -> float:
        """Calculate the Net Present Value based on Price to Earnings."""
        growth_safety_pe = stock.stock_data.growth_estimate * 0.75
        future_pe = (
            stock.stock_data.current_eps
            * stock.stock_data.historical_pe
            * ((1.0 + growth_safety_pe) ** 5)
        )
        stock.stock_data.pe = round(float(future_pe / ((1.0 + discount_rate) ** 5)), 2)

    @staticmethod
    def calculate_roe_npv(
        discount_rate: float,
        stock: Stock,
        margin_of_safety: float = 0.25,
    ) -> float:
        """Calculate the Net Present Value based on Return on Equity."""
        conservative_growth = stock.stock_data.growth_estimate * (1 - margin_of_safety)
        shareholders_equity = [
            stock.stock_data.stockholders_equity_raw
            * (1 + conservative_growth)
            / stock.stock_data.shares_outstanding_raw
        ]
        dividends = [
            stock.stock_data.trailing_dividend_rate_raw * (1 + conservative_growth)
        ]
        npv_dividends = [dividends[0] / (1 + discount_rate)]

        for i in range(1, 10):
            shareholders_equity.append(
                shareholders_equity[-1] * (1 + conservative_growth)
            )
            dividends.append(dividends[-1] * (1 + conservative_growth))
            npv_dividends.append(dividends[-1] / ((1 + discount_rate) ** (i + 1)))

        y10_net_income = shareholders_equity[-1] * stock.stock_data.historical_roe / 100
        required_value = y10_net_income / discount_rate
        npv_required_value = required_value / ((1 + discount_rate) ** 10)
        stock.stock_data.roe = round(float(sum(npv_dividends) + npv_required_value), 2)

    @staticmethod
    def calculate_dcf_npv(
        discount_rate: float,
        stock: Stock,
        margin_of_safety: float = 0.25,
    ) -> float:
        """Calculate the Net Present Value based on Discounted Cash Flow."""
        conservative_growth = stock.stock_data.growth_estimate * (1 - margin_of_safety)
        growth_decline = 0.05
        free_cash_growth = [stock.stock_data.fcf_raw_value * (1 + conservative_growth)]
        npv_free_cash = [free_cash_growth[0] / (1 + discount_rate)]

        for i in range(1, 10):
            free_cash_growth.append(
                free_cash_growth[-1]
                * (1 + conservative_growth * ((1 - growth_decline) ** i))
            )
            npv_free_cash.append(
                free_cash_growth[-1] / ((1 + discount_rate) ** (i + 1))
            )

        total_npv = sum(npv_free_cash)
        year_10_free_cash = npv_free_cash[-1] * 12
        stock.stock_data.dcf = round(
            float(
                (
                    total_npv
                    + year_10_free_cash
                    + stock.stock_data.cash_raw_eq
                    - stock.stock_data.liabilities
                )
                / stock.stock_data.shares_outstanding_raw
            ),
            2,
        )

    @staticmethod
    def fetch_historical_pe(ticker: yahooquery.Ticker) -> float:
        """Fetch 5-year historical PE from Yahoo Finance."""
        try:
            avg_historical_price = ticker.history(period="5y", interval="3mo")[
                "close"
            ].mean()
            avg_historical_eps = ticker.get_financial_data("BasicEPS")[
                "BasicEPS"
            ].mean()
            historical_pe = avg_historical_price / avg_historical_eps
            return historical_pe
        except Exception as e:
            logging.error(f"Error fetching historical PE: {e}")
            return 0.0

    @staticmethod
    def fetch_morningstar_roe(symbol: str, exchange: str, basic_data: dict) -> float:
        """Fetch 5-year historical ROE from Morningstar."""

        MORNINGSTAR_ROE_URL = "https://www.morningstar.com/stocks/%$%/$%$/performance"
        MORNING_STAR_EXCHANGE = {
            "nas": "xnas",
            "nyse": "xnys",
            "tsx": "xtse",
            "cse": "xcse",
        }

        ms_exchange = MORNING_STAR_EXCHANGE.get(exchange)
        url = MORNINGSTAR_ROE_URL.replace("$%$", symbol).replace("%$%", ms_exchange)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

        try:
            driver.get(url)

            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mds-tbody__sal"))
            )

            table = driver.find_element(By.CLASS_NAME, "mds-tbody__sal")
            rows = table.find_elements(By.TAG_NAME, "tr")

            if len(rows) < 2:
                logging.warning(f"Table does not have enough rows for {symbol}")
                return 0.0

            second_row = rows[2]
            columns = second_row.find_elements(By.TAG_NAME, "td")

            if len(columns) < 2:
                logging.warning(f"Second row does not have enough columns for {symbol}")
                return 0.0

            roe_value = columns[-2].text.strip()

            if "--" in roe_value:
                logging.warning(
                    f"No 5-year historical ROE available in MorningStar for {symbol}"
                )
                return (
                    StockFactory.extract_from_dict(
                        basic_data, StockFactory.key_paths["ReturnOnEquity"]
                    )
                    * 100
                )

            return float(roe_value)

        except Exception as e:
            logging.error(f"Error fetching MorningStar ROE for {symbol}: {e}")
            return 0.0

        finally:
            driver.quit()

    @staticmethod
    def extract_from_dict(data_dict: dict, key_path: list):
        try:
            for key in key_path:
                if isinstance(key, int):
                    data_dict = data_dict[key]
                else:
                    data_dict = data_dict.get(key, {})
            return data_dict if data_dict else 0.0
        except (KeyError, IndexError, TypeError):
            return 0.0

    @staticmethod
    def get_financial_value(
        df: pd.DataFrame, column_name: str, basic_stock_info: dict
    ) -> float | int:
        ttm_value = df.iloc[-1].get(column_name)
        if pd.notna(ttm_value):
            return ttm_value

        prev_year_value = df.iloc[-2].get(column_name)
        if pd.notna(prev_year_value):
            return prev_year_value

        if column_name == "FreeCashFlow":
            return StockFactory.calculate_free_cash_flow(basic_stock_info)

        return StockFactory.extract_from_dict(
            basic_stock_info, StockFactory.key_paths.get(column_name, [])
        )

    @staticmethod
    def calculate_free_cash_flow(basic_stock_info: dict) -> float:
        try:
            cashflow_statements = basic_stock_info.get(
                "cashflowStatementHistoryQuarterly", {}
            ).get("cashflowStatements", [])
            fcf_raw_value = sum(
                [
                    cashflow_statements[j].get("totalCashFromOperatingActivities", 0)
                    + cashflow_statements[j].get("capitalExpenditures", 0)
                    for j in range(4)
                    if j < len(cashflow_statements)
                ]
            )
            return fcf_raw_value
        except (KeyError, IndexError, TypeError):
            return 0.0

    @staticmethod
    def create_stock(symbol: str, exchange: str) -> Stock:
        """Create a stock object with the given symbol and exchange."""
        yh_symbol = get_stock_symbol_for_yahoo(symbol, exchange)
        ticker = yahooquery.Ticker(yh_symbol)
        basic_ticker: dict = ticker.all_modules
        if not isinstance(basic_ticker, dict):
            raise BadStock(f"Error fetching data for {symbol}")

        basic_ticker = basic_ticker[yh_symbol]
        if not isinstance(basic_ticker, dict):
            if isinstance(basic_ticker, str):
                raise BadStock(basic_ticker)
            raise BadStock(f"Error fetching data for {symbol}")

        current_price = basic_ticker.get("price", {}).get("regularMarketPrice", None)
        if current_price is None:
            raise BadStock(
                f"Current Price not available. Insufficient data for {symbol}"
            )

        financial_modules = [
            "MarketCap",
            "TotalRevenue",
            "NetIncome",
            "TotalAssets",
            "TotalLiabilitiesNetMinorityInterest",
            "TotalDebt",
            "LongTermDebt",
            "CashAndCashEquivalents",
            "FreeCashFlow",
            "StockholdersEquity",
        ]
        financial_ticker: pd.DataFrame = ticker.get_financial_data(
            financial_modules, trailing=True
        )
        if not isinstance(financial_ticker, pd.DataFrame):
            raise BadStock(f"Error fetching financial data for {symbol}")

        stock_data = StockData(
            current_price=current_price,
            pe=0,
            dcf=0,
            roe=0,
            quality=StockQuality.UNKNOWN,
            title=basic_ticker.get("quoteType", {}).get("longName", None),
            industry=basic_ticker.get("assetProfile", {}).get("industry", None),
            market_cap=StockFactory.get_financial_value(
                financial_ticker, "MarketCap", basic_ticker
            ),
            revenue=StockFactory.get_financial_value(
                financial_ticker, "TotalRevenue", basic_ticker
            ),
            net_income=StockFactory.get_financial_value(
                financial_ticker, "NetIncome", basic_ticker
            ),
            assets=StockFactory.get_financial_value(
                financial_ticker, "TotalAssets", basic_ticker
            ),
            liabilities=StockFactory.get_financial_value(
                financial_ticker, "TotalLiabilitiesNetMinorityInterest", basic_ticker
            ),
            debt=StockFactory.get_financial_value(
                financial_ticker, "TotalDebt", basic_ticker
            ),
            esg_score=basic_ticker.get("esgScores", {}).get("totalEsg", None),
            controversy=basic_ticker.get("esgScores", {}).get(
                "highestControversy", None
            ),
            summary=basic_ticker.get("summaryProfile", {}).get(
                "longBusinessSummary", None
            ),
            long_term_debt=StockFactory.get_financial_value(
                financial_ticker, "LongTermDebt", basic_ticker
            ),
            # growth_estimate=StockFactory.fetch_external_growth_estimate(symbol, exchange),
            growth_estimate=basic_ticker.get("earningsTrend", {})
            .get(
                "trend",
                [
                    {},
                    {},
                    {},
                    {},
                    {},
                ],
            )[4]
            .get("growth", None),
            current_eps=basic_ticker.get("defaultKeyStatistics", {}).get(
                "trailingEps", None
            ),
            historical_pe=StockFactory.fetch_historical_pe(ticker),
            cash_raw_eq=StockFactory.get_financial_value(
                financial_ticker, "CashAndCashEquivalents", basic_ticker
            ),
            fcf_raw_value=StockFactory.get_financial_value(
                financial_ticker, "FreeCashFlow", basic_ticker
            ),
            shares_outstanding_raw=basic_ticker.get("defaultKeyStatistics", {}).get(
                "sharesOutstanding", None
            ),
            stockholders_equity_raw=StockFactory.get_financial_value(
                financial_ticker, "StockholdersEquity", basic_ticker
            ),
            historical_roe=StockFactory.fetch_morningstar_roe(
                symbol, exchange, basic_ticker
            ),
            trailing_dividend_rate_raw=basic_ticker.get("summaryDetail", {}).get(
                "trailingAnnualDividendRate", None
            ),
            last_updated=int(time.time()),
        )

        stock = Stock(symbol, exchange, stock_data)

        StockFactory.validate_growth_estimate(stock)
        if stock.stock_data.growth_estimate != 0:
            try:
                StockFactory.calculate_pe_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logging.error(f"Error calculating PE NPV for {symbol}: {e}")
                pass

            try:
                StockFactory.calculate_roe_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logging.error(f"Error calculating ROE NPV for {symbol}: {e}")
                pass

            try:
                StockFactory.calculate_dcf_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logging.error(f"Error calculating DCF NPV for {symbol}: {e}")
                pass

        StockFactory.determine_and_update_stock_quality(stock)

        return stock

    @staticmethod
    def create_stock_from_data(
        symbol: str, exchange: str, stock_data: StockData
    ) -> Stock:
        """Create a stock object with the given symbol, exchange, and stock data."""
        stock = Stock(symbol, exchange, stock_data)
        return stock
    
    @staticmethod
    def create_bad_stock(symbol: str, exchange: str) -> Stock:
        """Create a bad stock object with the given symbol and exchange."""
        stock_data = StockData(
            current_price=0,
            pe=0,
            dcf=0,
            roe=0,
            quality=StockQuality.BAD,
            title="",
            industry="",
            market_cap=0,
            revenue=0,
            net_income=0,
            assets=0,
            liabilities=0,
            debt=0,
            esg_score=0,
            controversy=0,
            summary="",
            long_term_debt=0,
            growth_estimate=0,
            current_eps=0,
            historical_pe=0,
            cash_raw_eq=0,
            fcf_raw_value=0,
            shares_outstanding_raw=0,
            stockholders_equity_raw=0,
            historical_roe=0,
            trailing_dividend_rate_raw=0,
            last_updated=int(time.time()),
        )
        return Stock(symbol, exchange, stock_data)


def get_stock_symbol_for_yahoo(symbol: str, exchange: str) -> str:
    """Format symbols for Yahoo query."""
    if exchange.lower() == "tsx":
        return f"{symbol.upper()}.TO"
    elif exchange.lower() == "cse":
        return f"{symbol.upper()}.CN"
    else:
        return symbol.upper()
