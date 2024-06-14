from json import loads
import time
import logging
import requests
import yahooquery
from bs4 import BeautifulSoup
from stonk_list import update_stonk, connect_to_database, DB_FILE_PATH
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
YAHOO_API_RETRY_LIMIT = 2
DISCOUNT_RATE = 0.09
MORNINGSTAR_PE_URL = "http://financials.morningstar.com/valuate/current-valuation-list.action?&t={}&region=can&culture=en-US"
MORNINGSTAR_PE_URL = 'https://www.morningstar.com/stocks/%$%/$%$/valuation'
MORNINGSTAR_ROE_URL = 'https://www.morningstar.com/stocks/%$%/$%$/performance'

MORNING_STAR_EXCHANGE = {
    "xnas": "xnas",
    "xnyse": "xnyse",
    "tsx": "xtse",
    "cse": "xcse"
}

@dataclass
class StockData:
    title: str
    industry: str
    current_price: float
    quarterly_liabilities: float
    quarterly_assets: float
    long_term_debt: float
    net_income: float
    revenue: float
    market_cap: float
    growth_estimate: float
    current_eps: float
    historical_pe: float
    cash_raw_eq: float
    liabilities_raw: float
    fcf_raw_value: float
    shares_outstanding_raw: float
    stockholders_equity_raw: float
    historical_roe: float
    trailing_dividend_rate_raw: float

class BadStock(Exception):
    pass

class JustSkip(Exception):
    pass

class ExistingStock(Exception):
    pass

class RecentlyUpdated(Exception):
    pass

def calculate_roe_npv(discount_rate, equity, equity_rate, shares_outstanding, dividend_rate, growth_rate, margin_of_safety):
    """Calculate the Net Present Value based on Return on Equity."""
    conservative_growth = growth_rate * (1 - margin_of_safety)
    shareholders_equity = [equity * (1 + conservative_growth) / shares_outstanding]
    dividends = [dividend_rate * (1 + conservative_growth)]
    npv_dividends = [dividends[0] / (1 + discount_rate)]

    for i in range(1, 10):
        shareholders_equity.append(shareholders_equity[-1] * (1 + conservative_growth))
        dividends.append(dividends[-1] * (1 + conservative_growth))
        npv_dividends.append(dividends[-1] / ((1 + discount_rate) ** (i + 1)))

    y10_net_income = shareholders_equity[-1] * equity_rate
    required_value = y10_net_income / discount_rate
    npv_required_value = required_value / ((1 + discount_rate) ** 10)
    npv_value = npv_required_value + sum(npv_dividends)

    return int(npv_value)

def calculate_dcf_npv(discount_rate, cash_and_cash_eq, liabilities, free_cash_flow, outstanding_shares, growth_rate, margin_of_safety):
    """Calculate the Net Present Value based on Discounted Cash Flow."""
    conservative_growth = growth_rate * (1 - margin_of_safety)
    growth_decline = 0.05
    free_cash_growth = [free_cash_flow * (1 + conservative_growth)]
    npv_free_cash = [free_cash_growth[0] / (1 + discount_rate)]

    for i in range(1, 10):
        free_cash_growth.append(free_cash_growth[-1] * (1 + conservative_growth * ((1 - growth_decline) ** i)))
        npv_free_cash.append(free_cash_growth[-1] / ((1 + discount_rate) ** (i + 1)))

    total_npv = sum(npv_free_cash)
    year_10_free_cash = npv_free_cash[-1] * 12
    npv_dcf = (total_npv + year_10_free_cash + cash_and_cash_eq - liabilities) / outstanding_shares

    return npv_dcf

def fetch_morningstar_pe(symbol: list):
    """Fetch 5-year historical PE ratio from Morningstar."""
    exchange = MORNING_STAR_EXCHANGE.get(symbol[1])
    symbol = symbol[0].split(".")[0]
    url = MORNINGSTAR_PE_URL.replace('$%$', symbol).replace('%$%', exchange)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
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
            return None
        
        second_row = rows[2]
        columns = second_row.find_elements(By.TAG_NAME, "td")
        
        if len(columns) < 7:
            logging.warning(f"Second row does not have enough columns for {symbol}")
            return None
        
        pe_ratio = columns[-2].text.strip()

        if pe_ratio == '--':
            logging.info(f"5-year historical PE ratio not directly available for {symbol}. Calculating from adjacent columns.")

            pe_values = []
            for i in range(-8, -3):
                value = columns[i].text.strip()
                if value.replace('.', '', 1).isdigit():
                    pe_values.append(float(value))
            
            if len(pe_values) == 5:
                average_pe = sum(pe_values) / len(pe_values)
                logging.info(f"Calculated 5-year historical PE ratio for {symbol}: {average_pe}")
                return average_pe
            else:
                logging.warning(f"Insufficient data to calculate 5-year historical PE ratio for {symbol}.")
                return None
        else:
            return float(pe_ratio)

    except Exception:
        logging.error(f"Error fetching 5-year historical PE ratio for {symbol}")
        return None

    finally:
        driver.quit()

def fetch_morningstar_roe(symbol: list):
    """Fetch 5-year historical ROE from Morningstar."""
    exchange = MORNING_STAR_EXCHANGE.get(symbol[1])
    symbol = symbol[0].split(".")[0]
    url = MORNINGSTAR_ROE_URL.replace('$%$', symbol).replace('%$%', exchange)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
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
            return None

        second_row = rows[2]
        columns = second_row.find_elements(By.TAG_NAME, "td")

        if len(columns) < 2:
            logging.warning(f"Second row does not have enough columns for {symbol}")
            return None

        roe_value = columns[-2].text.strip()

        if '--' in roe_value:
            logging.warning(f"No 5-year historical ROE available for {symbol}")
            return None

        return float(roe_value)

    except Exception:
        logging.error(f"Error fetching 5-year historical ROE for {symbol}")
        return None

    finally:
        driver.quit()

def fetch_stock_data(symbol: str):
    """Fetch stock data using Yahoo Finance API."""
    try:
        ticker = yahooquery.Ticker(symbol[0]).all_modules
        return ticker[symbol[0]]
    except (requests.exceptions.RequestException, KeyError) as e:
        logging.error(f"Error fetching stock data for {symbol}: {e}")
        raise JustSkip

def analyze_symbols(symbol_list, iteration=0):
    """Analyze the given list of symbols."""
    for i, symbol in enumerate(symbol_list):
        logging.info(f"Analyzing {symbol[0]} ({i + 1}/{len(symbol_list)})")

        try:
            stock_data = fetch_stock_data(symbol)
            if isinstance(stock_data, str):
                logging.warning(f"Stock {symbol} not found. Skipping.")
                continue
            analyze_stock(symbol, stock_data, iteration)
        except JustSkip:
            logging.info(f"Skipping {symbol} due to previous errors.")
            continue

def analyze_stock(symbol: list, stock_data: dict, iteration: int):
    """Analyze individual stock and update database."""
    try:
        if iteration == 0:
            check_existing_stock(symbol)
            check_recent_update(symbol)

        stock = extract_stock_data(symbol, stock_data)
        if not stock.historical_pe:
            logging.warning(f"Skipping {symbol} due to missing historical PE ratio.")
            raise BadStock(f"Missing historical PE ratio for {symbol}")
        
        # validate_growth_estimate(symbol, stock.growth_estimate)

        calculate_and_update_stock_value(
            symbol,
            stock.title,
            stock.industry,
            stock.current_price,
            stock.quarterly_liabilities,
            stock.quarterly_assets,
            stock.long_term_debt,
            stock.net_income,
            stock.revenue,
            stock.market_cap,
            stock.growth_estimate,
            stock.current_eps,
            stock.historical_pe,
            stock.cash_raw_eq,
            stock.liabilities_raw,
            stock.fcf_raw_value,
            stock.shares_outstanding_raw,
            stock.stockholders_equity_raw,
            stock.historical_roe,
            stock.trailing_dividend_rate_raw
        )
    except (BadStock, ExistingStock, RecentlyUpdated):
        logging.info(f"Stock {symbol} is not eligible for further analysis.")
        return


def check_existing_stock(symbol: str):
    """Check if the stock already exists in the database."""
    with connect_to_database(DB_FILE_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stonks WHERE symbol=?", (symbol,))
        if cur.fetchone():
            raise ExistingStock(f"Stock {symbol} already exists.")

def check_recent_update(symbol: str):
    """Check if the stock was recently updated."""
    with connect_to_database(DB_FILE_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT last_updated FROM stonks WHERE symbol=?", (symbol,))
        result = cur.fetchone()
        if result and time.time() - result[0] < 43200:  # 12 hours in seconds
            raise RecentlyUpdated(f"Stock {symbol} was recently updated.")

def extract_stock_data(symbol: str, stock_data: dict) -> StockData:
    """Extract relevant data from stock_data dictionary."""
    try:
        title = stock_data.get("quoteType", {}).get("longName", None)
        industry = stock_data.get("summaryProfile", {}).get("industry", None)
        current_price = stock_data.get("price", {}).get("regularMarketPrice", None)
        
        # Use try-except for accessing list elements
        try:
            quarterly_liabilities = stock_data.get("balanceSheetHistoryQuarterly", {}).get("balanceSheetStatements", [{}])[0].get("totalLiab", None)
        except IndexError:
            quarterly_liabilities = None
        
        try:
            quarterly_assets = stock_data.get("balanceSheetHistoryQuarterly", {}).get("balanceSheetStatements", [{}])[0].get("totalAssets", None)
        except IndexError:
            quarterly_assets = None

        try:
            long_term_debt = stock_data.get("balanceSheetHistoryQuarterly", {}).get("balanceSheetStatements", [{}])[0].get("longTermDebt", None)
        except IndexError:
            long_term_debt = None

        try:
            net_income = stock_data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [{}])[0].get("netIncome", None)
        except IndexError:
            net_income = None

        try:
            revenue = stock_data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [{}])[0].get("totalRevenue", None)
        except IndexError:
            revenue = None

        market_cap = stock_data.get("summaryDetail", {}).get("marketCap", None)

        try:
            growth_estimate = stock_data.get("earningsTrend", {}).get("trend", [{}])[4].get("growth", None)
        except IndexError:
            growth_estimate = None

        current_eps = stock_data.get("defaultKeyStatistics", {}).get("trailingEps", None)
        historical_pe = fetch_morningstar_pe(symbol)

        try:
            cash_raw_eq = stock_data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [{}])[0].get("cash", None)
        except IndexError:
            cash_raw_eq = None

        try:
            liabilities_raw = stock_data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [{}])[0].get("totalLiab", None)
        except IndexError:
            liabilities_raw = None

        # Calculate fcf_raw_value with sum, handle missing data gracefully
        fcf_raw_value = sum([
            stock_data.get('cashflowStatementHistoryQuarterly', {}).get('cashflowStatements', [{}])[j].get('totalCashFromOperatingActivities', 0) +
            stock_data.get('cashflowStatementHistoryQuarterly', {}).get('cashflowStatements', [{}])[j].get('capitalExpenditures', 0)
            for j in range(4) if j < len(stock_data.get('cashflowStatementHistoryQuarterly', {}).get('cashflowStatements', []))
        ])

        shares_outstanding_raw = stock_data.get("defaultKeyStatistics", {}).get("sharesOutstanding", None)

        try:
            stockholders_equity_raw = stock_data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [{}])[0].get("totalStockholderEquity", None)
        except IndexError:
            stockholders_equity_raw = None

        historical_roe = fetch_morningstar_roe(symbol)
        trailing_dividend_rate_raw = stock_data.get("summaryDetail", {}).get("trailingAnnualDividendRate", None)

        return StockData(
            title=title,
            industry=industry,
            current_price=current_price,
            quarterly_liabilities=quarterly_liabilities,
            quarterly_assets=quarterly_assets,
            long_term_debt=long_term_debt,
            net_income=net_income,
            revenue=revenue,
            market_cap=market_cap,
            growth_estimate=growth_estimate,
            current_eps=current_eps,
            historical_pe=historical_pe,
            cash_raw_eq=cash_raw_eq,
            liabilities_raw=liabilities_raw,
            fcf_raw_value=fcf_raw_value,
            shares_outstanding_raw=shares_outstanding_raw,
            stockholders_equity_raw=stockholders_equity_raw,
            historical_roe=historical_roe,
            trailing_dividend_rate_raw=trailing_dividend_rate_raw
        )

    except Exception as e:
        logging.error(f"Error extracting data for {symbol}: {e}")
        return None

def validate_growth_estimate(symbol: str, growth_estimate):
    """Validate if the growth estimate is a float."""
    if not isinstance(growth_estimate, (float, int)):
        logging.warning(f"Growth estimate for {symbol} is not a valid number. Skipping.")
        raise BadStock(f"Invalid growth estimate for {symbol}")

def calculate_and_update_stock_value(symbol, title, industry, current_price, quarterly_liabilities, quarterly_assets, 
                                     long_term_debt, net_income, revenue, market_cap, growth_estimate, 
                                     current_eps, historical_pe, cash_raw_eq, liabilities_raw, fcf_raw_value, 
                                     shares_outstanding_raw, stockholders_equity_raw, historical_roe, 
                                     trailing_dividend_rate_raw):
    """Calculate stock value and update in the database."""
    pe_value = calculate_pe_value(current_eps, historical_pe, growth_estimate)
    dcf_value = calculate_dcf_value(cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw, growth_estimate)
    roe_value = calculate_roe_value(stockholders_equity_raw, historical_roe, shares_outstanding_raw, trailing_dividend_rate_raw, growth_estimate)

    quality = determine_stock_quality(current_price, pe_value, dcf_value, roe_value)

    stonk_data = [current_price, pe_value, dcf_value, roe_value, symbol[1], quality, title, industry, 
                  market_cap, revenue, net_income, quarterly_assets, quarterly_liabilities, long_term_debt, 
                  "", "", "", int(time.time())]

    update_stonk(symbol[0], stonk_data)

def calculate_pe_value(current_eps, historical_pe, growth_estimate):
    """Calculate the price based on PE ratio."""
    try:
        growth_safety_pe = growth_estimate * 0.75
        future_pe = current_eps * historical_pe * ((1.0 + growth_safety_pe) ** 5)
        return int(future_pe / ((1.0 + DISCOUNT_RATE) ** 5))
    except Exception as e:
        logging.error(f"Error calculating PE value: {e}")
        return 0

def calculate_dcf_value(cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw, growth_estimate):
    """Calculate the price based on DCF model."""
    try:
        return calculate_dcf_npv(DISCOUNT_RATE, cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw, growth_estimate, 0.25)
    except Exception as e:
        logging.error(f"Error calculating DCF value: {e}")
        return 0

def calculate_roe_value(stockholders_equity_raw, historical_roe, shares_outstanding_raw, trailing_dividend_rate_raw, growth_estimate):
    """Calculate the price based on ROE model."""
    try:
        return calculate_roe_npv(DISCOUNT_RATE, stockholders_equity_raw, historical_roe / 100, shares_outstanding_raw, trailing_dividend_rate_raw, growth_estimate, 0.25)
    except Exception as e:
        logging.error(f"Error calculating ROE value: {e}")
        return 0

def determine_stock_quality(current_price, pe_value, dcf_value, roe_value):
    """Determine the quality of the stock based on calculated values."""
    good_values = [value for value in [pe_value, dcf_value, roe_value] if current_price < value]
    if len(good_values) == 3:
        return "Good"
    elif len(good_values) == 2:
        return "Okay"
    return "Bad"

def is_float(value):
    """Check if the value can be converted to a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False
