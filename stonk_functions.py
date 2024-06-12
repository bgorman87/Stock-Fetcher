from json import loads
import time
import logging
import requests
import yahooquery
from bs4 import BeautifulSoup
from stonk_list import update_stonk, connect_to_database, DB_FILE_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
YAHOO_API_RETRY_LIMIT = 2
DISCOUNT_RATE = 0.09
MORNINGSTAR_PE_URL = "http://financials.morningstar.com/valuate/current-valuation-list.action?&t={}&region=can&culture=en-US"
MORNINGSTAR_ROE_URL = "http://financials.morningstar.com/finan/financials/getKeyStatPart.html?&t={}"

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

def fetch_morningstar_pe(symbol: str):
    """Fetch PE ratio from Morningstar."""
    try:
        response = requests.get(MORNINGSTAR_PE_URL.format(symbol))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.find(id="currentValuationTable")
        rows = table.find_all('tr')

        for row in rows:
            data = [td.get_text(strip=True) for td in row.find_all('td')]
            if data:
                return float(data[3])  # Assuming the PE is in the fourth column
    except (requests.exceptions.RequestException, ValueError, IndexError, AttributeError) as e:
        logging.error(f"Error fetching PE ratio for {symbol}: {e}")
        return None

def fetch_morningstar_roe(symbol: str):
    """Fetch ROE from Morningstar."""
    try:
        response = requests.get(MORNINGSTAR_ROE_URL.format(symbol))
        response.raise_for_status()
        data = loads(response.text)['componentData']
        soup = BeautifulSoup(data, "html5lib")
        rows = soup.find_all('td')

        roe_values = [float(td.get_text()) for td in rows if "i26" in str(td)]
        if roe_values:
            return sum(roe_values) / len(roe_values)
    except (requests.exceptions.RequestException, ValueError, AttributeError) as e:
        logging.error(f"Error fetching ROE for {symbol}: {e}")
        return None

def fetch_stock_data(symbol: str):
    """Fetch stock data using Yahoo Finance API."""
    try:
        ticker = yahooquery.Ticker(symbol).all_modules
        return ticker[symbol]
    except (requests.exceptions.RequestException, KeyError) as e:
        logging.error(f"Error fetching stock data for {symbol}: {e}")
        raise JustSkip

def analyze_symbols(symbol_list, iteration=0):
    """Analyze the given list of symbols."""
    for i, symbol in enumerate(symbol_list):
        logging.info(f"Analyzing {symbol} ({i + 1}/{len(symbol_list)})")

        try:
            # Fetch stock data
            stock_data = fetch_stock_data(symbol)
            analyze_stock(symbol, stock_data, iteration)
        except JustSkip:
            logging.info(f"Skipping {symbol} due to previous errors.")
            continue

def analyze_stock(symbol: str, stock_data, iteration: int):
    """Analyze individual stock and update database."""
    try:
        if iteration == 0:
            check_existing_stock(symbol)
            check_recent_update(symbol)

        title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
        revenue, market_cap, growth_estimate, current_eps, historical_pe, cash_raw_eq, liabilities_raw, \
        fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_roe, \
        trailing_dividend_rate_raw = extract_stock_data(stock_data)

        validate_growth_estimate(symbol, growth_estimate)

        calculate_and_update_stock_value(symbol, title, industry, current_price, quarterly_liabilities, quarterly_assets, 
                                         long_term_debt, net_income, revenue, market_cap, growth_estimate, 
                                         current_eps, historical_pe, cash_raw_eq, liabilities_raw, fcf_raw_value, 
                                         shares_outstanding_raw, stockholders_equity_raw, historical_roe, 
                                         trailing_dividend_rate_raw)
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

def extract_stock_data(symbol: str,  stock_data: str) -> tuple:
    """Extract relevant data from stock_data dictionary."""
    try:
        title = stock_data["quoteType"].get("longName", "")
        industry = stock_data["summaryProfile"].get("industry", "")
        current_price = stock_data["price"].get("regularMarketPrice", 0)
        quarterly_liabilities = stock_data["balanceSheetHistoryQuarterly"]["balanceSheetStatements"][0].get("totalLiab", 0)
        quarterly_assets = stock_data["balanceSheetHistoryQuarterly"]["balanceSheetStatements"][0].get("totalAssets", 0)
        long_term_debt = stock_data["balanceSheetHistoryQuarterly"]["balanceSheetStatements"][0].get("longTermDebt", 0)
        net_income = stock_data["incomeStatementHistory"]["incomeStatementHistory"][0].get("netIncome", 0)
        revenue = stock_data["incomeStatementHistory"]["incomeStatementHistory"][0].get("totalRevenue", 0)
        market_cap = stock_data["summaryDetail"].get("marketCap", 0)
        growth_estimate = stock_data["earningsTrend"]["trend"][4].get("growth", 0)
        current_eps = stock_data["defaultKeyStatistics"].get("trailingEps", 0)
        historical_pe = fetch_morningstar_pe(symbol)
        cash_raw_eq = stock_data["balanceSheetHistory"]["balanceSheetStatements"][0].get("cash", 0)
        liabilities_raw = stock_data["balanceSheetHistory"]["balanceSheetStatements"][0].get("totalLiab", 0)
        fcf_raw_value = sum([
            stock_data['cashflowStatementHistoryQuarterly']['cashflowStatements'][j]['totalCashFromOperatingActivities'] +
            stock_data['cashflowStatementHistoryQuarterly']['cashflowStatements'][j]['capitalExpenditures']
            for j in range(4)
        ])
        shares_outstanding_raw = stock_data["defaultKeyStatistics"].get("sharesOutstanding", 0)
        stockholders_equity_raw = stock_data["balanceSheetHistory"]["balanceSheetStatements"][0].get("totalStockholderEquity", 0)
        historical_roe = fetch_morningstar_roe(symbol)
        trailing_dividend_rate_raw = stock_data["summaryDetail"].get("trailingAnnualDividendRate", 0)

        return title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
               revenue, market_cap, growth_estimate, current_eps, historical_pe, cash_raw_eq, liabilities_raw, \
               fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_roe, trailing_dividend_rate_raw

    except KeyError as e:
        logging.error(f"Error extracting data for {symbol}: {e}")
        raise JustSkip(f"Missing data for {symbol}")

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

    stonk_data = [current_price, pe_value, dcf_value, roe_value, "Exchange Placeholder", quality, title, industry, 
                  market_cap, revenue, net_income, quarterly_assets, quarterly_liabilities, long_term_debt, 
                  "", "", "", int(time.time())]

    update_stonk(symbol, stonk_data)

def calculate_pe_value(current_eps, historical_pe, growth_estimate):
    """Calculate the price based on PE ratio."""
    if current_eps and historical_pe:
        growth_safety_pe = growth_estimate * 0.75
        future_pe = current_eps * historical_pe * ((1.0 + growth_safety_pe) ** 5)
        return int(future_pe / ((1.0 + DISCOUNT_RATE) ** 5))
    return 0

def calculate_dcf_value(cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw, growth_estimate):
    """Calculate the price based on DCF model."""
    if cash_raw_eq and liabilities_raw and fcf_raw_value and shares_outstanding_raw:
        return calculate_dcf_npv(DISCOUNT_RATE, cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw, growth_estimate, 0.25)
    return 0

def calculate_roe_value(stockholders_equity_raw, historical_roe, shares_outstanding_raw, trailing_dividend_rate_raw, growth_estimate):
    """Calculate the price based on ROE model."""
    if stockholders_equity_raw and historical_roe and shares_outstanding_raw and trailing_dividend_rate_raw:
        return calculate_roe_npv(DISCOUNT_RATE, stockholders_equity_raw, historical_roe / 100, shares_outstanding_raw, trailing_dividend_rate_raw, growth_estimate, 0.25)
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
