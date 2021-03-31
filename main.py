from stonk_functions import *
from stonk_list import *
import yahooquery
import urllib3
import re


########################################################################################################################

# TODO  - Save calculated values into json file.
#       - Possibly Chart/Graph Results
#       - Some sort of system to automatically import stock symbols into a master list
#       - Some sort of notification when PE/DCF/ROE is higher than the current stock price.
#           - In this notification, maybe list the industry and in future maybe some symbols the I can use to compare

# What this program should do

# Check what currency the financial statements are in.

# Run through the list of all stocks every 2 days (Approx 3000 stocks so will take about 20 Hours)
# Once completed and a good symbols list is compiled run through good symbols and determine which ones are best
# Good symbols list will probably be between 70-90 symbols so reduce list somehow to around 10.

# Run full list (~20h)
# Run analysis on good symbols (~1h)
# Sleep (12h) or until mid market day maybe
# Run analysis on good symbols (~1h)
# Sleep (12h) or until mid market day maybe
# Repeat

# Currently outputs an excel file.
# Create function that goes through each excel file and stores the data for each symbol.
# Once stored, it then puts everything together in a new excel workbook
# where each sheet can be a separate piece of data with graph showing historical trend.

# Still need to look at what else i can find from a company.
# Maybe sort the data by ratio, then top 10 create a separate sheet for and input even more data for those 10?

# Additional information to grab
# P/E (TTM) - From summary page of yahoo finance

########################################################################################################################


class SkipStock(Exception):
    pass


class JustSkip(Exception):
    pass


class ExistingStock(Exception):
    pass


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
        except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError):
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
        return title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, revenue, \
            market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, fcf_raw_value, \
            shares_outstanding_raw, stockholders_equity_raw, historical_ROE, trailing_dividend_rate_raw, ticker
    except JustSkip:
        return title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, revenue, \
            market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, fcf_raw_value, \
            shares_outstanding_raw, stockholders_equity_raw, historical_ROE, trailing_dividend_rate_raw, ticker


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
                                 "Liabilities": 0, "Debt": 0, "ESG Score": 0, "Controversy": 0}}
        print("---------------------------------------")
        print(f"Analyzing {symbol.split('.')[0]} - {exchange_fmt} - {i + 1}/{len(master_symbol_list)}")

        try:
            if skip_existing:
                with open('Stonks Files\\Output\\stock_data.txt', 'r') as json_file:
                    stonks = json.load(json_file)
                try:
                    _ = stonks[symbol]
                    raise ExistingStock
                except KeyError:
                    pass

            title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, revenue, \
            market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, fcf_raw_value, \
            shares_outstanding_raw, stockholders_equity_raw, historical_ROE, trailing_dividend_rate_raw, ticker = \
                stock_stats(symbol)

            if not is_float(growth_estimate):
                growth_estimate_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/analysis?p={yahoo_symbol}"
                print_string = f"Growth Estimate Not Found For: {symbol} - {growth_estimate_link}"
                print(print_string)
                remove_symbol(removed_symbol=symbol, e=print_string)
                raise SkipStock(print_string)

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
                remove_symbol(removed_symbol=symbol, e=print_string)
                raise SkipStock(print_string)

            print(symbol, " - ", title)

            new_stonk["Exchange"] = exchange_fmt
            new_stonk["Current"] = current_price
            new_stonk["P/E"] = current_5y_backtrack_pe
            new_stonk["DCF"] = current_10y_backtrack_dcf
            new_stonk["ROE"] = current_10y_backtrack_roe
            new_stonk["Title"] = title

            if print_bool:
                print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")
                print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")
                print(f"Current Price Based on ROE 10y Estimate: ${current_10y_backtrack_roe}")

            prices = [current_5y_backtrack_pe, current_10y_backtrack_dcf, current_10y_backtrack_roe]
            good_prices = [price for price in prices if current_price < price]
            quality = "Bad"
            if len(good_prices) == 3:
                print(symbol, ": Could be a good investment, added to good symbol list.")
                quality = "Good"
                add_good_symbol(symbol, quality=quality)
            elif len(good_prices) == 2:
                if 0 in good_prices:
                    print(symbol, ": Could be a good investment, not all information available though,"
                                  " added to good symbol list.")
                else:
                    print(symbol, ": Could be a good investment, needs a manual check though,"
                                  " added to good symbol list.")
                quality = "Okay"
                add_good_symbol(symbol, quality=quality)

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
        except SkipStock as e:
            remove_symbol(removed_symbol=symbol, e=str(e), update_list=True)
            continue
        except ExistingStock:
            print(f"{symbol} is already in stock_data.txt : Skipping for now")
            continue
        # except (ValueError, TypeError) as e:
        #     continue

    remove_symbol(update_list=True)


########################################################################################################################

def update_good_spreadsheets(good_symbols):
    yahoo_symbols = []
    for x, symbol in enumerate(good_symbols):
        if ".to" in symbol or ".cn" in symbol:
            yahoo_symbols.append(symbol.upper())
        else:
            yahoo_symbols.append(symbol.split(".")[0])

    good_tickers = yahooquery.Ticker(yahoo_symbols)
    good_recommendations = good_tickers.recommendations
    good_tickers = good_tickers.all_modules
    template_file = "Stonks Files\\Individual Good Symbol Spreadsheets\\!Individual Good Symbol Template.xlsx"
    for x, symbol in enumerate(good_symbols):

        industry = ""
        title = ""
        current_price = ""
        market_cap = ""
        revenue = ""
        net_income = ""
        quarterly_assets = ""
        quarterly_liabilities = ""
        long_term_debt = ""
        esg_score = ""
        controversy_level = ""
        summary = ""
        current_5y_backtrack_pe = 0
        current_10y_backtrack_dcf = 0
        current_10y_backtrack_roe = 0
        discount_rate = 0.09
        try:
            _ = good_tickers[yahoo_symbols[x]]
            wb = load_workbook(template_file)
            stonks_ws = wb["Stats"]
            with open("Stonks Files\\Output\\stock_data.txt", "r") as local_file:
                stonks = json.load(local_file)
            retrieve_stonk_data = False
            try:
                _ = stonks[symbol]
                title = stonks[symbol]["Title"]
                industry = stonks[symbol]["Details"]["Industry"]
                current_price = stonks[symbol]["Current"]
                summary = stonks[symbol]["Details"]["Summary"]
                esg_score = stonks[symbol]["Details"]["ESG Score"]
                controversy_level = stonks[symbol]["Details"]["Controversy"]
                market_cap = stonks[symbol]["Details"]["Market Cap"]
                revenue = stonks[symbol]["Details"]["Revenue"]
                quarterly_assets = stonks[symbol]["Details"]["Assets"]
                quarterly_liabilities = stonks[symbol]["Details"]["Liabilities"]
                long_term_debt = stonks[symbol]["Details"]["Debt"]
                net_income = stonks[symbol]["Details"]["Net Income"]
                current_10y_backtrack_roe = stonks[symbol]["P/E"]
                current_10y_backtrack_dcf = stonks[symbol]["DCF"]
                current_5y_backtrack_pe = stonks[symbol]["ROE"]
            except (TypeError, ValueError, KeyError) as e:
                print(e)
                retrieve_stonk_data = True
                pass
            if retrieve_stonk_data:
                title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, revenue, \
                market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, fcf_raw_value, \
                shares_outstanding_raw, stockholders_equity_raw, historical_ROE, trailing_dividend_rate_raw, _ \
                    = stock_stats(yahoo_symbols[x])

                if not is_float(growth_estimate):
                    growth_estimate_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbols[x]}/analysis?p" \
                                           f"={yahoo_symbols[x]} "
                    print_string = f"Growth Estimate Not Found For: {symbol} - {growth_estimate_link}"
                    print(print_string)
                    raise JustSkip(print_string)

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

            file_title = str(title).strip().replace(' ', '_')
            file_title = re.sub(r'(?u)[^-\w.]', '', file_title)
            file_save = "Stonks Files\\Individual Good Symbol Spreadsheets\\" + symbol.split(".")[0] + " - " + \
                        file_title + ".xlsx"

            stonks_ws.cell(3, 1).value = symbol
            stonks_ws.cell(3, 2).value = industry
            stonks_ws.cell(3, 3).value = title
            stonks_ws.cell(3, 4).value = current_price
            stonks_ws.cell(3, 5).value = current_5y_backtrack_pe
            stonks_ws.cell(3, 6).value = current_10y_backtrack_dcf
            stonks_ws.cell(3, 7).value = current_10y_backtrack_roe
            stonks_ws.cell(3, 8).value = market_cap
            stonks_ws.cell(3, 9).value = revenue
            stonks_ws.cell(3, 10).value = net_income
            stonks_ws.cell(3, 11).value = quarterly_assets
            stonks_ws.cell(3, 12).value = quarterly_liabilities
            stonks_ws.cell(3, 14).value = long_term_debt
            stonks_ws.cell(3, 16).value = esg_score
            stonks_ws.cell(3, 17).value = controversy_level
            stonks_ws.cell(3, 18).value = summary
        except (KeyError, ValueError, TypeError, JustSkip) as e:
            print(e)
            continue

        try:
            recommended = good_recommendations[yahoo_symbols[x]]['recommendedSymbols']
            recommended = [item["symbol"] for item in recommended]
            row = 8
            for recommended_symbol in recommended:
                try:

                    industry = ""
                    title = ""
                    current_price = ""
                    market_cap = ""
                    revenue = ""
                    net_income = ""
                    quarterly_assets = ""
                    quarterly_liabilities = ""
                    long_term_debt = ""
                    esg_score = ""
                    controversy_level = ""
                    summary = ""
                    current_5y_backtrack_pe = 0
                    current_10y_backtrack_dcf = 0
                    current_10y_backtrack_roe = 0
                    discount_rate = 0.09

                    title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
                    revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, \
                    fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_ROE, \
                    trailing_dividend_rate_raw, _ = stock_stats(recommended_symbol)

                    # Calculations
                    if is_float(growth_estimate) and is_float(current_EPS) and is_float(historical_PE):
                        growth_safety_pe = growth_estimate * 0.75
                        future_5y_estimate_pe = float(current_EPS) * float(historical_PE) *\
                                                ((1.0 + growth_safety_pe) ** 5)
                        current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + discount_rate) ** 5))
                    else:
                        current_5y_backtrack_pe = 0

                    if is_float(growth_estimate) and is_float(cash_raw_eq) and is_float(liabilities_raw) and is_float(fcf_raw_value) and is_float(
                            shares_outstanding_raw):
                        if int(shares_outstanding_raw) != 0:
                            current_10y_backtrack_dcf = int(
                                get_dcf_npv(discount_rate, cash_raw_eq, liabilities_raw, fcf_raw_value,
                                            shares_outstanding_raw, growth_estimate, 0.25))
                        else:
                            current_10y_backtrack_dcf = 0
                    else:
                        current_10y_backtrack_dcf = 0

                    if is_float(growth_estimate) and is_float(stockholders_equity_raw) and is_float(historical_ROE) and is_float(
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

                    stonks_ws.cell(row, 1).value = recommended_symbol
                    stonks_ws.cell(row, 2).value = industry
                    stonks_ws.cell(row, 3).value = title
                    stonks_ws.cell(row, 4).value = current_price
                    stonks_ws.cell(row, 5).value = current_5y_backtrack_pe
                    stonks_ws.cell(row, 6).value = current_10y_backtrack_dcf
                    stonks_ws.cell(row, 7).value = current_10y_backtrack_roe
                    stonks_ws.cell(row, 8).value = market_cap
                    stonks_ws.cell(row, 9).value = revenue
                    stonks_ws.cell(row, 10).value = net_income
                    stonks_ws.cell(row, 11).value = quarterly_assets
                    stonks_ws.cell(row, 12).value = quarterly_liabilities
                    stonks_ws.cell(row, 14).value = long_term_debt
                    stonks_ws.cell(row, 16).value = esg_score
                    stonks_ws.cell(row, 17).value = controversy_level
                    stonks_ws.cell(row, 18).value = summary
                    row += 1
                except JustSkip:
                    continue

        except (KeyError, ValueError, TypeError) as e:
            print(e)
            continue
        try:
            if "News" in wb.sheetnames:
                good_news = yahooquery.Ticker(yahoo_symbols[x])
                good_news = good_news.news()
                stonks_ws = wb["News"]
                for i in range(len(good_news)):
                    stonks_ws.cell(i + 8, 1).hyperlink = good_news[i]["url"]
                    stonks_ws.cell(i + 8, 1).value = good_news[i]["title"]
                    for k in range(2):
                        if k == 0:
                            author = "author_name"
                        else:
                            author = "provider_name"
                        try:
                            stonks_ws.cell(i + 8, 4).value = good_news[i][author]
                            break
                        except (KeyError, ValueError, TypeError):
                            stonks_ws.cell(i + 8, 4).value = ""
                    stonks_ws.cell(i + 8, 5).value = good_news[i]["summary"]
        except (KeyError, ValueError, TypeError):
            continue
        wb.save(file_save)
        wb.close()


########################################################################################################################

update_spreadsheet(get_good_symbols("okay"))

testing = True
symbol_count = 0
iter_count = 1
if not testing:
    while True:
        start_whole = time.perf_counter()

        start_full_list = time.perf_counter()
        master_list = get_symbols(symbol_count)
        stop_full_list = time.perf_counter()

        start_analyze = time.perf_counter()
        analyze_symbols(master_list, iter_count)
        stop_analyze = time.perf_counter()

        if iter_count > 1:
            start_analyze_good = time.perf_counter()
            update_spreadsheet()
            stop_analyze_good = time.perf_counter()
        else:
            start_analyze_good = time.perf_counter()
            stop_analyze_good = time.perf_counter()
        #
        # if iter_count > 1:
        #     # 43200s == 12h
        #     time.sleep(43200)

        start_analyze2 = time.perf_counter()
        analyze_symbols(get_good_symbols(), iter_count)
        stop_analyze2 = time.perf_counter()

        start_update_good = time.perf_counter()
        update_good_spreadsheets(get_good_symbols())
        stop_update_good = time.perf_counter()

        start_analyze_good2 = time.perf_counter()
        update_spreadsheet()
        stop_analyze_good2 = time.perf_counter()

        # Un-necessary to check everytime, check every 3rd iteration
        if iter_count == 1 or iter_count % 3 == 0:
            start_analyze_removed = time.perf_counter()
            analyze_symbols(get_removed_symbols())
            stop_analyze_removed = time.perf_counter()
        else:
            start_analyze_removed = time.perf_counter()
            stop_analyze_removed = time.perf_counter()

        stop_whole = time.perf_counter()

        print_output = f"\nTimer Info for iteration {iter_count}\n" \
                       f"Master List: {round(stop_full_list - start_full_list, 2)}s\n" \
                       f"Analyze Full: {round(stop_analyze - start_analyze, 2)}s\n" \
                       f"Update Spreadsheet: {round(stop_analyze_good - start_analyze_good, 2)}s\n" \
                       f"Analyze Good: {round(stop_analyze2 - start_analyze2, 2)}s\n" \
                       f"Update Spreadsheet 2: {round(stop_analyze_good2 - start_analyze_good2, 2)}s\n" \
                       f"Update Good Spreadsheets: {round(stop_update_good - start_update_good, 2)}s\n" \
                       f"Analyze Removed: {round(stop_analyze_removed - start_analyze_removed, 2)}s\n" \
                       f"Total Run Time: {round(stop_whole - start_whole, 2)}s\n"

        print("\n---------------------------------------")
        print(print_output)
        print("---------------------------------------\n")

        with open("Stonks Files\\Output\\output.txt", "a") as file:
            file.write("\n---------------------------------------")
            file.write(print_output)
            file.write("---------------------------------------\n")
        if iter_count > 2:
            time.sleep(43200)
        iter_count += 1
