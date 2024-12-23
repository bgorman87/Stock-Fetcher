from dataclasses import dataclass
from enum import Enum
import pandas as pd
import time
import logging
import yahooquery
from datetime import datetime
import feedparser
from utils import BadStock
from feedparser import FeedParserDict

logger = logging.getLogger(__name__)

class StockQuality(Enum):
    GREAT = 1
    GOOD = 2
    OKAY = 3
    BAD = 4


@dataclass
class News:
    id: str
    title: str | None = None
    summary: str | None = None
    url: str | None = None
    author_name: str | None = None
    provider_name: str | None = None
    provider_publish_time: datetime | None = None


@dataclass
class StockData:
    current_price: float | None = None
    pe: float | None = None
    dcf: float | None = None
    roe: float | None = None
    quality: StockQuality = StockQuality.BAD
    title: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    revenue: float | None = None
    net_income: float | None = None
    assets: float | None = None
    liabilities: float | None = None
    debt: float | None = None
    esg_score: float | None = None
    controversy: float | None = None
    summary: str | None = None
    long_term_debt: float | None = None
    growth_estimate: float | None = None
    current_eps: float | None = None
    historical_pe: float | None = None
    cash_raw_eq: float | None = None
    fcf_raw_value: float | None = None
    shares_outstanding_raw: float | None = None
    stockholders_equity_raw: float | None = None
    historical_roe: float | None = None
    trailing_dividend_rate_raw: float | None = None
    last_updated: float | None = None
    news: list[News] | None = None

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

        y10_net_income = shareholders_equity[-1] * stock.stock_data.historical_roe
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
    def fetch_historical_pe(ticker: yahooquery.Ticker) -> float | None:
        """Fetch 5-year historical PE from Yahoo Finance."""
        try:
            avg_historical_price = ticker.history(period="5y", interval="3mo")[
                "close"
            ].mean()
            basic_eps = ticker.get_financial_data("BasicEPS")
            if isinstance(basic_eps, str):
                raise AttributeError(basic_eps)
            avg_historical_eps = basic_eps.get(
                "BasicEPS"
            , []).mean()
            historical_pe = avg_historical_price / avg_historical_eps
            return float(historical_pe)
        except AttributeError as e:
            logger.error(f"Historical ROE Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching historical PE: {e}")
            return None
        
    @staticmethod
    def extract_from_dict(data_dict: dict, key_path: list) -> float | None:
        try:
            for key in key_path:
                if isinstance(key, int):
                    data_dict = data_dict[key]
                else:
                    data_dict = data_dict.get(key, {})
            return float(data_dict) if data_dict else 0.0
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def get_financial_value(
        df: pd.DataFrame, column_name: str, basic_stock_info: dict
    ) -> float | None:
        try:
            if column_name == "HistoricalROE":
                df_12m = df[df['periodType'] == '12M']
                if df_12m.empty:
                    return None
                
                roe_values = []
                for i in range(len(df_12m)):
                    net_income = df_12m.iloc[i].get("NetIncome")
                    equity = df_12m.iloc[i].get("StockholdersEquity")
                    
                    if pd.notna(net_income) and pd.notna(equity) and equity != 0:
                        roe = net_income / equity
                        roe_values.append(roe)
                
                if roe_values:
                    return float(sum(roe_values) / len(roe_values))
                return None

            if column_name in df.columns:
                df_values = df[column_name].dropna()
                if not df_values.empty:
                    return float(df_values.iloc[-1])

            if column_name == "FreeCashFlow":
                fcf_value = StockFactory.calculate_free_cash_flow(basic_stock_info)
                if not fcf_value:
                    fcf_value = df[df['periodType'] == 'TTM'].iloc[0].get(column_name)
                    if pd.notna(fcf_value):
                        return float(fcf_value)
                return fcf_value

            return StockFactory.extract_from_dict(
                basic_stock_info, StockFactory.key_paths.get(column_name, [])
            )
        except Exception as e:
            logger.error(f"Error fetching financial value for {column_name}: {e}")
            return None


    @staticmethod
    def calculate_free_cash_flow(basic_stock_info: dict) -> float | None:
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
            return float(fcf_raw_value) if fcf_raw_value else None
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def get_news_from_yahoo(ticker_symbol: str) -> list[News]:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker_symbol}"
        feed: FeedParserDict = feedparser.parse(url)

        news_list = []
        for entry in feed.entries:
            try:
                news = News(id=entry.id)
                news.title = entry.title
                news.summary = entry.summary
                news.url = entry.link
                news.provider_name = "Yahoo Finance"
                news.provider_publish_time = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed)
                )
                news_list.append(news)
            except AttributeError as e:
                logger.error(f"RSS News Error: {e}")
                continue
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
                continue

        return news_list

    @staticmethod
    def create_stock(symbol: str, exchange: str) -> Stock:
        """Create a stock object with the given symbol and exchange."""
        yh_symbol = get_stock_symbol_for_yahoo(symbol, exchange)
        ticker = yahooquery.Ticker(yh_symbol)

        stock_data = StockData()
        time_interval = {0: 300, 1: 600, 2: 1200}
        for i, interval in list(time_interval.items()):
            basic_ticker: dict = ticker.all_modules
            if not isinstance(basic_ticker, dict):
                raise BadStock(stock_data, f"Error fetching data for {symbol}")
            
            if isinstance(basic_ticker[yh_symbol], str):
                if "for input string" in basic_ticker[yh_symbol].lower():
                   logger.error(f"Iteration {i+1} - earningsTrend returning error. Sleeping for {interval}s...")
                   time.sleep(interval)
            else:
                break

        if isinstance(basic_ticker[yh_symbol], str):
            if "for input string" in basic_ticker[yh_symbol].lower():
                raise ValueError(f"Error getting all modules: {basic_ticker[yh_symbol]}")

        basic_ticker = basic_ticker[yh_symbol]
        if not isinstance(basic_ticker, dict):
            if isinstance(basic_ticker, str):
                raise BadStock(stock_data, basic_ticker)
            raise BadStock(stock_data, f"Error fetching data for {symbol}")

        stock_data.news = StockFactory.get_news_from_yahoo(yh_symbol)

        current_price = basic_ticker.get("price", {}).get("regularMarketPrice", None)
        if current_price is None:
            raise BadStock(
                stock_data,
                f"Current Price not available. Insufficient data for {symbol}",
            )

        stock_data.current_price = current_price
        stock_data.title = (basic_ticker.get("quoteType", {}).get("longName", None),)
        stock_data.industry = (
            basic_ticker.get("assetProfile", {}).get("industry", None),
        )
        stock_data.esg_score = (
            basic_ticker.get("esgScores", {}).get("totalEsg", None),
        )
        stock_data.controversy = basic_ticker.get("esgScores", {}).get(
            "highestControversy", None
        )
        stock_data.summary = basic_ticker.get("summaryProfile", {}).get(
            "longBusinessSummary", None
        )
        stock_data.growth_estimate = (
            basic_ticker.get("earningsTrend", {})
            .get(
                "trend",
                [
                    {},
                    {},
                    {},
                    {},
                ],
            )[3]
            .get("growth", None)
        )
        stock_data.current_eps = basic_ticker.get("defaultKeyStatistics", {}).get(
            "trailingEps", None
        )
        stock_data.shares_outstanding_raw = basic_ticker.get(
            "defaultKeyStatistics", {}
        ).get("sharesOutstanding", None)
        stock_data.trailing_dividend_rate_raw = basic_ticker.get(
            "summaryDetail", {}
        ).get("trailingAnnualDividendRate", None)

        stock_data.historical_pe = StockFactory.fetch_historical_pe(ticker)

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
            raise BadStock(stock_data, f"Error fetching financial data for {symbol}")

        stock_data.historical_roe = StockFactory.get_financial_value(
            financial_ticker, "HistoricalROE", basic_ticker
        )

        stock_data.market_cap = StockFactory.get_financial_value(
            financial_ticker, "MarketCap", basic_ticker
        )
        stock_data.revenue = StockFactory.get_financial_value(
            financial_ticker, "TotalRevenue", basic_ticker
        )
        stock_data.net_income = StockFactory.get_financial_value(
            financial_ticker, "NetIncome", basic_ticker
        )
        stock_data.assets = StockFactory.get_financial_value(
            financial_ticker, "TotalAssets", basic_ticker
        )
        stock_data.liabilities = StockFactory.get_financial_value(
            financial_ticker, "TotalLiabilitiesNetMinorityInterest", basic_ticker
        )
        stock_data.debt = StockFactory.get_financial_value(
            financial_ticker, "TotalDebt", basic_ticker
        )
        stock_data.long_term_debt = StockFactory.get_financial_value(
            financial_ticker, "LongTermDebt", basic_ticker
        )
        stock_data.cash_raw_eq = StockFactory.get_financial_value(
            financial_ticker, "CashAndCashEquivalents", basic_ticker
        )
        stock_data.fcf_raw_value = StockFactory.get_financial_value(
            financial_ticker, "FreeCashFlow", basic_ticker
        )
        stock_data.stockholders_equity_raw = StockFactory.get_financial_value(
            financial_ticker, "StockholdersEquity", basic_ticker
        )

        stock_data.last_updated = int(time.time())

        stock = Stock(symbol, exchange, stock_data)

        StockFactory.validate_growth_estimate(stock)
        if stock.stock_data.growth_estimate != 0:
            try:
                StockFactory.calculate_pe_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logger.error(f"Error calculating PE NPV for {symbol}: {e}")
                stock.stock_data.pe = None
                pass

            try:
                StockFactory.calculate_roe_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logger.error(f"Error calculating ROE NPV for {symbol}: {e}")
                stock.stock_data.roe = None
                pass

            try:
                StockFactory.calculate_dcf_npv(StockFactory.DISCOUNT_RATE, stock)
            except Exception as e:
                logger.error(f"Error calculating DCF NPV for {symbol}: {e}")
                stock.stock_data.dcf = None
                pass

        return stock

    @staticmethod
    def create_stock_from_data(
        symbol: str, exchange: str, stock_data: StockData
    ) -> Stock:
        """Create a stock object with the given symbol, exchange, and stock data."""
        stock = Stock(symbol, exchange, stock_data)
        return stock


def get_stock_symbol_for_yahoo(symbol: str, exchange: str) -> str:
    """Format symbols for Yahoo query."""
    if exchange.lower() == "tsx":
        return f"{symbol.upper()}.TO"
    elif exchange.lower() == "cse":
        return f"{symbol.upper()}.CN"
    else:
        return symbol.upper()
