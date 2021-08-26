import json
import time
import urllib3
import yahooquery

import requests
from bs4 import BeautifulSoup

from stonk_list import data_update

print_bool = False


class BadStock(Exception):
    pass


class JustSkip(Exception):
    pass


class ExistingStock(Exception):
    pass


class RecentlyUpdated(Exception):
    pass


def get_roe_npv(discount_rate, equity, equity_rate, shares_outstanding, dividend_rate, growth_rate, margin_of_safety):
    conservative_growth = growth_rate * (1 - margin_of_safety)
    shareholders_equity = []
    dividend = []
    npv_dividend = []
    shareholders_equity.append(equity * (1 + conservative_growth) / shares_outstanding)
    dividend.append(dividend_rate * (1 + conservative_growth))
    npv_dividend.append(dividend[0])
    for i in range(2, 11):
        shareholders_equity.append(shareholders_equity[i - 2] * (1 + conservative_growth))
        dividend.append(dividend[i - 2] * (1 + conservative_growth))
        npv_dividend.append(dividend[i - 1] / ((1 + discount_rate) ** (i - 1)))
    y10_net_income = shareholders_equity[-1] * equity_rate
    required_value = y10_net_income / discount_rate
    npv_required_value = required_value / ((1 + discount_rate) ** len(dividend))
    npv_dividends = sum(npv_dividend)
    npv_value = npv_required_value + npv_dividends
    return int(npv_value)


def get_dcf_npv(discount_rate, cash_and_cash_eq, liabilities, free_cash_flow, outstanding_shares,
                growth_rate, margin_of_safety):
    conservative_growth = growth_rate * (1 - margin_of_safety)
    growth_decline = 0.05
    free_cash_growth = []
    npv_free_cash = []
    free_cash_growth.append(free_cash_flow * (1 + conservative_growth))
    npv_free_cash.append(free_cash_growth[0] / (1 + discount_rate))
    for i in range(2, 11):
        free_cash_growth.append(
            free_cash_growth[i - 2] * (1 + (conservative_growth * ((1 - growth_decline) ** (i - 1)))))
        npv_free_cash.append(free_cash_growth[i - 1] / ((1 + discount_rate) ** i))

    total_npv = sum(npv_free_cash)
    year_10_free_cash = npv_free_cash[-1] * 12

    npv_dcf = (total_npv + year_10_free_cash + cash_and_cash_eq - liabilities) / outstanding_shares

    return npv_dcf


def row_get_Data_Text(tr, coltag='td'):  # td (data) or th (header)
    return [td.get_text(strip=True) for td in tr.find_all(coltag)]


def get_morningstar_pe(local_symbol):
    historical_PE_link = "http://financials.morningstar.com/valuate/current-valuation-list.action?&t" \
                         "={}&region=can&culture=en-US"
    link = historical_PE_link.format(local_symbol)
    values = []
    try:
        html_content = requests.get(link).text
        soup = BeautifulSoup(html_content, "lxml")
        table = soup.find(
            lambda tag: tag.name == 'table' and tag.has_attr('id') and tag['id'] == "currentValuationTable")
        rows = table.findAll(lambda tag: tag.name == 'tr')
        for row in rows:
            values.append(row_get_Data_Text(row, 'td'))
    except (requests.exceptions.RequestException, ValueError, AttributeError, KeyError, TypeError):
        pass
        # print(e)
    if values:
        try:
            return values[3][3]
        except IndexError:
            return values
    else:
        return values


def get_morningstar_roe(local_symbol):
    historical_ROE_link = "http://financials.morningstar.com/finan/financials/getKeyStatPart.html?&t={}"
    link = historical_ROE_link.format(local_symbol)
    values = []
    content_rows = []
    try:
        html_content = requests.get(link).text
        test = json.loads(html_content)
        soup = BeautifulSoup(test['componentData'], "html5lib")
        rows = soup.findAll(lambda tag: tag.name == 'td')

        for row in rows:
            if "i26" in str(row):
                content_rows.append(row)
    except (requests.exceptions.RequestException, ValueError, AttributeError, KeyError, TypeError):
        pass
        # print(e)
    if content_rows:
        values = [value.get_text() for value in content_rows]
    for i, value in enumerate(values):
        if not is_float(value):
            values[i] = 0
    if values:
        return sum([float(value) for value in values[5:-1]]) / 5
    else:
        return values


## Stock Scraping
def stock_stats(local_symbol, print_bool_analyze=False):
    title = ""
    industry = ""
    current_price = ""
    quarterly_liabilities = ""
    quarterly_assets = ""
    long_term_debt = ""
    net_income = ""
    revenue = ""
    market_cap = ""
    ticker = ""
    future_5y_estimate_pe = ""
    growth_estimate = ""
    current_EPS = ""
    historical_PE = ""
    cash_raw_eq = ""
    liabilities_raw = ""
    fcf_raw_value = ""
    shares_outstanding_raw = ""
    stockholders_equity_raw = ""
    historical_ROE = ""
    trailing_dividend_rate_raw = ""

    try:
        morningstar_symbol = local_symbol.split(".")[0]
        yahoo_symbol = local_symbol.split(".")[0]
        if ".to" in local_symbol or ".to" in local_symbol:
            morningstar_symbol = "XTSE:" + local_symbol.split(".")[0]
            yahoo_symbol = local_symbol.upper()
        elif ".nas" in local_symbol:
            morningstar_symbol = "XNAS:" + local_symbol.split(".")[0]
        elif ".cn" in local_symbol:
            morningstar_symbol = "CNQ:" + local_symbol.split(".")[0]
            yahoo_symbol = local_symbol.upper()

        try:
            ticker = yahooquery.Ticker(yahoo_symbol).all_modules
        except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError,
                requests.exceptions.ConnectionError):
            print_string = f"No response when trying to get {local_symbol} information."
            print(print_string)
            raise JustSkip
        # title = get_yahoo_stat(yahoo_symbol, "title")
        try:
            title = ticker[yahoo_symbol]["quoteType"]["longName"]
        except (TypeError, KeyError, IndexError):
            title = local_symbol + ": Title not found"

        try:
            industry = ticker[yahoo_symbol]["summaryProfile"]["industry"]
        except (TypeError, KeyError, IndexError):
            industry = ""

        # growth_estimate = get_yahoo_stat(yahoo_symbol, "growth")
        try:
            growth_estimate = ticker[yahoo_symbol]["earningsTrend"]["trend"][4]["growth"]
        except (TypeError, KeyError, IndexError):
            growth_estimate = ""

        try:
            market_cap = ticker[yahoo_symbol]["summaryDetail"]["marketCap"]
        except (TypeError, KeyError, IndexError):
            market_cap = ""
            pass

        # current_EPS current_price = get_yahoo_stat(yahoo_symbol, "eps")
        try:
            current_EPS = ticker[yahoo_symbol]["defaultKeyStatistics"]["trailingEps"]
        except (TypeError, KeyError, IndexError):
            current_EPS = ""
            pass

        try:
            current_price = ticker[yahoo_symbol]["price"]["regularMarketPrice"]
        except (TypeError, KeyError, IndexError):
            current_price = 0

        historical_PE = ""
        for x in range(2):
            historical_PE = get_morningstar_pe(morningstar_symbol)
            if historical_PE:
                if is_float(historical_PE):
                    break
                else:
                    morningstar_symbol = local_symbol.split(".")[0]
            else:
                morningstar_symbol = local_symbol.split(".")[0]
            time.sleep(1)
        operating_activities = []
        capital_expenses = []
        fcf_raw_value = 0
        try:
            # fcf_raw_value, fcf_fmt_value = get_yahoo_stat(yahoo_symbol, "fcf")
            for j in range(4):
                operating_activities.append(ticker[yahoo_symbol]['cashflowStatementHistoryQuarterly'][
                                                'cashflowStatements'][j]['totalCashFromOperatingActivities'])
                capital_expenses.append(ticker[yahoo_symbol]['cashflowStatementHistoryQuarterly'][
                                            'cashflowStatements'][j]['capitalExpenditures'])
            for j in range(4):
                fcf_raw_value = fcf_raw_value + (int(operating_activities[j]) + int(capital_expenses[j]))
            fcf_fmt_value = fcf_raw_value
        except (TypeError, KeyError, IndexError):
            fcf_raw_value = ""
            fcf_fmt_value = ""

        historical_ROE = ""
        for x in range(2):
            historical_ROE = get_morningstar_roe(morningstar_symbol)
            if historical_ROE:
                if is_float(historical_ROE):
                    break
                else:
                    morningstar_symbol = local_symbol.split(".")[0]
            else:
                morningstar_symbol = local_symbol.split(".")[0]
            time.sleep(1)

        # cash_raw_eq, cash_fmt_eq, liabilities_raw, liabilities_fmt, stockholders_equity_raw, \
        # stockholders_equity_fmt, quarterly_assets, quarterly_liabilities, long_term_debt, net_income, revenue \
        #     = get_yahoo_stat(yahoo_symbol, "ceq")
        try:
            cash_raw_eq = ticker[yahoo_symbol]['balanceSheetHistory']['balanceSheetStatements'][0]['cash']
            cash_fmt_eq = cash_raw_eq
        except (TypeError, KeyError, IndexError):
            cash_fmt_eq = ""
            cash_raw_eq = ""
            pass
        try:
            liabilities_raw = ticker[yahoo_symbol]['balanceSheetHistory']['balanceSheetStatements'][0]['totalLiab']
            liabilities_fmt = liabilities_raw
        except (TypeError, KeyError, IndexError):
            liabilities_fmt = ""
            liabilities_raw = ""
            pass
        try:
            stockholders_equity_raw = ticker[yahoo_symbol]['balanceSheetHistory']['balanceSheetStatements'][0][
                'totalStockholderEquity']
            stockholders_equity_fmt = stockholders_equity_raw
        except (TypeError, KeyError, IndexError):
            stockholders_equity_fmt = ""
            stockholders_equity_raw = ""
            pass
        try:
            quarterly_assets = ticker[yahoo_symbol]['balanceSheetHistoryQuarterly']['balanceSheetStatements'][0][
                "totalAssets"]
        except (TypeError, KeyError, IndexError):
            quarterly_assets = ""
            pass
        try:
            quarterly_liabilities = ticker[yahoo_symbol]['balanceSheetHistoryQuarterly'][
                'balanceSheetStatements'][0]["totalLiab"]
        except (TypeError, KeyError, IndexError):
            quarterly_liabilities = ""
            pass
        try:
            long_term_debt = ticker[yahoo_symbol]['balanceSheetHistoryQuarterly']['balanceSheetStatements'][0][
                "longTermDebt"]
        except (TypeError, KeyError, IndexError):
            long_term_debt = ""
            pass
        try:
            net_income = ticker[yahoo_symbol]['incomeStatementHistory']['incomeStatementHistory'][0]["netIncome"]
        except (TypeError, KeyError, IndexError):
            net_income = ""
            pass
        try:
            revenue = ticker[yahoo_symbol]['incomeStatementHistory']['incomeStatementHistory'][0]["totalRevenue"]
        except (TypeError, KeyError, IndexError):
            revenue = ""
            pass

        # shares_outstanding_raw, shares_outstanding_fmt, trailing_dividend_rate_raw, trailing_dividend_rate_fmt,\
        #     market_cap = get_yahoo_stat(yahoo_symbol, "shares_outstanding")

        try:
            shares_outstanding_raw = ticker[yahoo_symbol]['defaultKeyStatistics']['sharesOutstanding']
            shares_outstanding_fmt = shares_outstanding_raw
        except (TypeError, KeyError, IndexError):
            shares_outstanding_fmt = ""
            shares_outstanding_raw = ""
            pass
        try:
            trailing_dividend_rate_raw = ticker[yahoo_symbol]['summaryDetail']['trailingAnnualDividendRate']
            trailing_dividend_rate_fmt = trailing_dividend_rate_raw
        except (TypeError, KeyError, IndexError):
            trailing_dividend_rate_fmt = ""
            trailing_dividend_rate_raw = ""
            pass

        if print_bool_analyze:
            print("------ P/E CALC -----")
            try:
                print("Historical Price/Earnings:", historical_PE)
            except ValueError:
                pass
            try:
                print("Trailing EPS:", current_EPS)
            except ValueError:
                pass
            try:
                print(f"Growth Estimate: {growth_estimate * 100}%")
            except ValueError:
                pass
            try:
                print(f"Future 5y Price: ${int(future_5y_estimate_pe)}")
            except ValueError:
                pass
            print("------ DCF CALC -----")
            try:
                print(f"Free Cash Flow: ${fcf_fmt_value}")
            except ValueError:
                pass
            try:
                print(f"Cash and Cash Equivalents: ${cash_fmt_eq}")
            except ValueError:
                pass
            try:
                print(f"Total Liabilities: ${liabilities_fmt}")
            except ValueError:
                pass
            try:
                print(f"Shares Outstanding: ${shares_outstanding_fmt}")
            except ValueError:
                pass
            print("------ ROE CALC -----")
            try:
                print("Historical Return on Equity:", round(historical_ROE, 2))
            except ValueError:
                pass
            try:
                print("Stockholders Equity:", stockholders_equity_fmt)
            except ValueError:
                pass
            try:
                print("Trailing Dividend Rate:", trailing_dividend_rate_fmt)
            except ValueError:
                pass
        return title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
               revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, \
               fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_ROE, \
               trailing_dividend_rate_raw, ticker
    except JustSkip:
        return title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
               revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, \
               fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_ROE, \
               trailing_dividend_rate_raw, ticker


########################################################################################################################

def analyze_symbols(master_symbol_list, iteration=0):
    discount_rate = 0.09
    if iteration >= 0:
        skip_existing = False
    else:
        skip_existing = True

    for i, symbol in enumerate(master_symbol_list):
        if iteration > 1:
            time.sleep(3)

        yahoo_symbol = symbol.split(".")[0]
        exchange_fmt = ""
        # Yahoo Finance needs .TO suffix for TSX and .CN for CSE
        #   But does not need a suffix for US stocks
        if ".to" in symbol:
            exchange_fmt = "TSX"
            yahoo_symbol = symbol.upper()
        elif ".nas" in symbol:
            exchange_fmt = "NASDAQ"
        elif ".nyse" in symbol:
            exchange_fmt = "NYSE"
        elif ".cn" in symbol:
            exchange_fmt = "CSE"
            yahoo_symbol = symbol.upper()

        new_stonk = {"Exchange": "", "Quality": "", "Current": 0, "P/E": 0, "DCF": 0, "ROE": 0, "Title": "",
                     "Details": {"Industry": "", "Market Cap": 0, "Revenue": 0, "Net Income": 0, "Assets": 0,
                                 "Liabilities": 0, "Debt": 0, "ESG Score": 0, "Controversy": 0},
                     "LastUpdated": time.gmtime(0)}
        print("---------------------------------------")
        print(f"Analyzing {symbol.split('.')[0]} - {exchange_fmt} - {i + 1}/{len(master_symbol_list)}")

        try:
            with open('Stonks Files\\Output\\stock_data.txt', 'r') as json_file:
                stonks = json.load(json_file)
                if skip_existing:
                    try:
                        _ = stonks[symbol]
                        raise ExistingStock
                    except KeyError:
                        pass
                try:
                    updated_time = int(stonks[symbol]["LastUpdated"])
                    if abs(int(time.time()) - updated_time) < (86400/2):  # 86400/2 s = 12h
                        raise RecentlyUpdated
                except (KeyError, ValueError):
                    pass

            title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
            revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, \
            fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_ROE, \
            trailing_dividend_rate_raw, ticker = \
                stock_stats(symbol)

            if not is_float(growth_estimate):
                growth_estimate_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/analysis?p={yahoo_symbol}"
                print_string = f"Growth Estimate Not Found For: {symbol} - {growth_estimate_link}"
                print(print_string)
                # Don't remove just set quality = Bad
                # remove_symbol(local_exchange_list, removed_symbol=symbol, e=print_string)
                raise BadStock(print_string)

            # Calculations
            if is_float(growth_estimate) and is_float(current_EPS) and is_float(historical_PE):
                growth_safety_pe = growth_estimate * 0.75
                future_5y_estimate_pe = float(current_EPS) * float(historical_PE) * ((1.0 + growth_safety_pe) ** 5)
                current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + discount_rate) ** 5))
            else:
                current_5y_backtrack_pe = 0

            if is_float(cash_raw_eq) and is_float(liabilities_raw) and is_float(fcf_raw_value) and is_float(
                    shares_outstanding_raw):
                if int(shares_outstanding_raw) != 0:
                    current_10y_backtrack_dcf = int(
                        get_dcf_npv(discount_rate, cash_raw_eq, liabilities_raw, fcf_raw_value,
                                    shares_outstanding_raw, growth_estimate, 0.25))
                else:
                    current_10y_backtrack_dcf = 0
            else:
                current_10y_backtrack_dcf = 0

            if is_float(stockholders_equity_raw) and is_float(historical_ROE) and is_float(
                    shares_outstanding_raw) and \
                    is_float(trailing_dividend_rate_raw):
                if int(shares_outstanding_raw) != 0:
                    current_10y_backtrack_roe = get_roe_npv(discount_rate, stockholders_equity_raw,
                                                            historical_ROE / 100, shares_outstanding_raw,
                                                            trailing_dividend_rate_raw, growth_estimate, 0.25)
                else:
                    current_10y_backtrack_roe = 0
            else:
                current_10y_backtrack_roe = 0

            zero_values = 0
            for value in [current_5y_backtrack_pe, current_10y_backtrack_dcf, current_10y_backtrack_roe]:
                if value == 0:
                    zero_values += 1
            if zero_values > 1:
                print_string = f"Multiple 0 values for P/E, DCF, ROE - Skipping stock: {symbol}"
                print(print_string)
                # Don't remove just set quality = Bad
                # remove_symbol(local_exchange_list, removed_symbol=symbol, e=print_string)
                raise BadStock(print_string)

            print(symbol, " - ", title)

            new_stonk["Exchange"] = exchange_fmt
            new_stonk["Current"] = current_price
            new_stonk["P/E"] = current_5y_backtrack_pe
            new_stonk["DCF"] = current_10y_backtrack_dcf
            new_stonk["ROE"] = current_10y_backtrack_roe
            new_stonk["Title"] = title
            new_stonk["LastUpdated"] = time.time()

            if print_bool:
                print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")
                print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")
                print(f"Current Price Based on ROE 10y Estimate: ${current_10y_backtrack_roe}")

            prices = [current_5y_backtrack_pe, current_10y_backtrack_dcf, current_10y_backtrack_roe]
            good_prices = [price for price in prices if current_price < price]
            quality = "Bad"
            if len(good_prices) == 3:
                print(symbol, ": Could be a good investment.")
                quality = "Good"
            elif len(good_prices) == 2:
                if 0 in good_prices:
                    print(symbol, ": Could be a good investment, not all information available though,"
                                  " added to good symbol list.")
                else:
                    print(symbol, ": Could be a good investment, needs a manual check though")
                quality = "Okay"

            new_stonk["Quality"] = quality
            if quality == "Good" or quality == "Okay":
                # industry, summary = get_yahoo_stat(yahoo_symbol, "profile")
                # esg_score, controversy_level = get_yahoo_stat(yahoo_symbol, "sustainability")
                try:
                    industry = ticker[yahoo_symbol]["summaryProfile"]["industry"]
                except (TypeError, KeyError, IndexError):
                    industry = ""
                    pass
                try:
                    summary = ticker[yahoo_symbol]["summaryProfile"]['longBusinessSummary']
                except (TypeError, KeyError, IndexError):
                    summary = ""
                    pass
                try:
                    esg_score = ticker[yahoo_symbol]["esgScores"]["totalEsg"]
                except (TypeError, KeyError, IndexError):
                    esg_score = ""
                    pass
                try:
                    controversy_level = ticker[yahoo_symbol]["esgScores"]["highestControversy"]
                except (TypeError, KeyError, IndexError):
                    controversy_level = ""
                    pass
                new_stonk["Details"]["Liabilities"] = quarterly_liabilities
                new_stonk["Details"]["Assets"] = quarterly_assets
                new_stonk["Details"]["Debt"] = long_term_debt
                new_stonk["Details"]["Net Income"] = net_income
                new_stonk["Details"]["Revenue"] = revenue
                new_stonk["Details"]["Industry"] = industry
                new_stonk["Details"]["Market Cap"] = market_cap
                new_stonk["Details"]["ESG Score"] = esg_score
                new_stonk["Details"]["Controversy"] = controversy_level
                new_stonk["Details"]["Summary"] = summary

            data_update(symbol, new_stonk)

            print(new_stonk)
        except BadStock:
            new_stonk["Quality"] = "Bad"
            data_update(symbol, new_stonk)
            continue
        except ExistingStock:
            print(f"{symbol} is already in stock_data.txt : Skipping for now")
            continue
        except RecentlyUpdated:
            print(f"{symbol} has been recently updated. Skipping data processing.")
            continue
        except KeyError as e:
            print(e)
            continue


def is_float(f):
    try:
        float(f)
        return True
    except (TypeError, ValueError):
        return False
