from stonk_functions import *
from stonk_list import *
from lowest_price import lowest_price


# TODO  - Save calculated values into json file.
#       - Possibly Chart/Graph Results
#       - Some sort of system to automatically import stock symbols into a master list
#       - Some sort of notification when PE/DCF/ROE is higher than the current stock price.
#           - In this notification, maybe list the industry and in future maybe some symbols the I can use to compare

# What this program should do

# Run through the list of all stocks every 2 days (Approx 3000 stocks so will take about 20 Hours)
# Once completed and a good symbols list is compiled run through good symbols and determine which ones are best
# Good symbols list will probably be between 70-90 symbols so reduce list somehow to around 10.

# Run full list (~20h)
# Run analysis on good symbols (~1h)
# Sleep (12h) or until mid market day maybe
# Run analysis on good symbols (~1h)
# Sleep (12h) or until mid market day maybe
# Repeat


class SkipStock(Exception):
    pass


class ExistingStock(Exception):
    pass


def analyze_symbols(master_symbol_list, iteration):
    print_bool_analyze = False
    discount_rate = 0.09
    growth_safety_pe = 0
    future_5y_estimate_pe = 0
    if iteration > 1:
        skip_existing = False
    else:
        skip_existing = True

    for i, symbol in enumerate(master_symbol_list):
        historical_PE = ""
        historical_ROE = ""
        current_EPS = ""
        current_price = ""

        morningstar_symbol = symbol.split(".")[0]
        yahoo_symbol = symbol.split(".")[0]
        exchange_fmt = ""
        # Yahoo Finance needs .TO suffix for TSX
        #   But does not need a suffix for US stocks
        if ".tsx" in symbol:
            exchange_fmt = "TSX"
            morningstar_symbol = "XTSE:" + symbol.split(".")[0]
            yahoo_symbol = symbol.split(".")[0] + ".TO"
        elif ".nas" in symbol:

            exchange_fmt = "NASDAQ"
            morningstar_symbol = "XNAS:" + symbol.split(".")[0]
        elif ".nyse" in symbol:
            exchange_fmt = "NYSE"

        new_stonk = {"Exchange": "", "Quality": "", "Current": 0, "P/E": 0, "DCF": 0, "ROE": 0}
        print(f"Analyzing {symbol.split('.')[0]} - {exchange_fmt} - {i + 1}/{len(master_symbol_list)}")

        try:
            if skip_existing:
                with open('stock_data.txt', 'r') as json_file:
                    stonks = json.load(json_file)
                try:
                    _ = stonks[symbol]
                    raise ExistingStock
                except KeyError:
                    pass
            ## Stock Scraping
            title = get_yahoo_stat(yahoo_symbol, "title")
            if not title:
                title = symbol + ": Title not found"

            growth_estimate = get_yahoo_stat(yahoo_symbol, "growth")
            if not is_float(growth_estimate):
                growth_estimate_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/analysis?p={yahoo_symbol}"
                print_string = f"Growth Estimate Not Found For: {symbol} - {growth_estimate_link}"
                print(print_string)
                remove_symbol(removed_symbol=symbol, e=print_string)
                raise SkipStock(print_string)
            try:
                current_EPS, current_price = get_yahoo_stat(yahoo_symbol, "eps")
            except ValueError:
                pass
            if not current_price:
                current_price = 0
            # if not is_float(current_EPS):
            #     current_eps_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}?p={yahoo_symbol}"
            #     print_string = f"Current EPS Not Found For: {symbol} - {current_eps_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            for x in range(2):
                historical_PE = get_morningstar_pe(morningstar_symbol)
                if historical_PE:
                    if is_float(historical_PE):
                        break
                    else:
                        morningstar_symbol = symbol.split(".")[0]
                else:
                    morningstar_symbol = symbol.split(".")[0]
                time.sleep(1)
            # if not is_float(historical_PE):
            #     historical_PE_link = f"http://financials.morningstar.com/valuate/current-valuation-list.action?&t" \
            #                          f"={morningstar_symbol}&region=can&culture=en-US"
            #     print_string = f"Historical PE Ratio Not Found For: {symbol} - {historical_PE_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            fcf_raw_value, fcf_fmt_value = get_yahoo_stat(yahoo_symbol, "fcf")
            # if not is_float(fcf_raw_value):
            #     fcf_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/cash-flow?p={yahoo_symbol}"
            #     print_string = f"Free Cash Flow Not Found For: {symbol} - {fcf_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            for x in range(2):
                historical_ROE = get_morningstar_roe(morningstar_symbol)
                if historical_ROE:
                    if is_float(historical_ROE):
                        break
                    else:
                        morningstar_symbol = symbol.split(".")[0]
                else:
                    morningstar_symbol = symbol.split(".")[0]
                time.sleep(1)
            # if not is_float(historical_ROE):
            #     historical_ROE_link = f"http://financials.morningstar.com/finan/financials/getKeyStatPart.html?&" \
            #                           f"t={morningstar_symbol}"
            #     print_string = f"Historical ROE Not Found For: {symbol} - {historical_ROE_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            cash_raw_eq, cash_fmt_eq, liabilities_raw, liabilities_fmt, stockholders_equity_raw, \
            stockholders_equity_fmt = get_yahoo_stat(yahoo_symbol, "ceq")
            # ceq_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/balance-sheet?p={yahoo_symbol}"
            # if not is_float(cash_raw_eq):
            #     print_string = f"Cash Equiv Not Found For: {symbol} - {ceq_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock
            # if not is_float(liabilities_raw):
            #     print_string = f"Liabilities Not Found For: {symbol} - {ceq_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock
            # if not is_float(stockholders_equity_raw):
            #     print_string = f"Stockholders Equity Not Found For: {symbol} - {ceq_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            shares_outstanding_raw, shares_outstanding_fmt, trailing_dividend_rate_raw, trailing_dividend_rate_fmt = \
                get_yahoo_stat(yahoo_symbol, "shares_outstanding")
            # if not is_float(shares_outstanding_raw):
            #     shares_outstanding_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/key-statistics?" \
            #                               f"p={yahoo_symbol}"
            #     print_string = f"Shares Outstanding Not Found For: {symbol} - {shares_outstanding_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock
            # if not is_float(trailing_dividend_rate_raw):
            #     shares_outstanding_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/key-statistics?" \
            #                               f"p={yahoo_symbol}"
            #     print_string = f"Trailing Dividend Not Found For: {symbol} - {shares_outstanding_link}"
            #     print(print_string)
            #     # remove_symbol(removed_symbol=symbol, e=print_string, exchange=exchange)
            #     # raise SkipStock

            # Calculations
            if is_float(growth_estimate) and is_float(current_EPS) and is_float(historical_PE):
                growth_safety_pe = growth_estimate * 0.75
                future_5y_estimate_pe = float(current_EPS) * float(historical_PE) * ((1.0 + growth_safety_pe) ** 5)
                current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + 0.12) ** 5))
            else:
                current_5y_backtrack_pe = 0

            if is_float(cash_raw_eq) and is_float(liabilities_raw) and is_float(fcf_raw_value) and is_float(
                    shares_outstanding_raw):
                if int(shares_outstanding_raw) != 0:
                    current_10y_backtrack_dcf = int(
                        get_dcf_npv(discount_rate, cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw,
                                    growth_estimate, 0.25))
                else:
                    current_10y_backtrack_dcf = 0
                    print("Possibly rate limited in financials section of Yahoo Finance.")
            else:
                current_10y_backtrack_dcf = 0
                print("Possibly rate limited in financials section of Yahoo Finance.")

            if is_float(stockholders_equity_raw) and is_float(historical_ROE) and is_float(shares_outstanding_raw) and \
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

            print(symbol, " - ", title.replace("Analyst Ratings, Estimates & Forecasts - Yahoo Finance", ""))
            new_stonk["Exchange"] = exchange_fmt

            new_stonk["Current"] = current_price

            new_stonk["P/E"] = current_5y_backtrack_pe
            print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")

            new_stonk["DCF"] = current_10y_backtrack_dcf
            print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")

            new_stonk["ROE"] = current_10y_backtrack_roe
            print(f"Current Price Based on ROE 10y Estimate: ${current_10y_backtrack_roe}")
            zero_values = []
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
            data_update(symbol, new_stonk)

            if print_bool_analyze:
                print("------ P/E CALC -----")
                print("Historical Price/Earnings:", historical_PE)
                print("Trailing EPS:", current_EPS)
                print(f"Growth Estimate: {growth_estimate * 100}%")
                print(f"Growth Safety Estimate: {round(growth_safety_pe * 100, 1)}%")
                print(f"Future 5y Price: ${int(future_5y_estimate_pe)}")
                print("------ DCF CALC -----")
                print(f"Free Cash Flow: ${fcf_fmt_value}")
                print(f"Cash and Cash Equivalents: ${cash_fmt_eq}")
                print(f"Total Liabilities: ${liabilities_fmt}")
                print(f"Shares Outstanding: ${shares_outstanding_fmt}")
                print("------ ROE CALC -----")
                print("Historical Return on Equity:", round(historical_ROE, 2))
                print("Stockholders Equity:", stockholders_equity_fmt)
                print("Trailing Dividend Rate:", trailing_dividend_rate_fmt)

            print(new_stonk)
        except SkipStock as e:
            remove_symbol(removed_symbol=symbol, e=str(e))
            continue
        except ExistingStock:
            print(f"{symbol} is already in stock_data.txt : Skipping for now")
            continue
        # except (ValueError, TypeError) as e:
        #     continue

    remove_symbol(update_list=True)


symbol_count = 0


def analyze_good_symbols(good_symbols):
    current_prices, current_ratios, symbols = lowest_price(good_symbols=good_symbols)
    zipped = list(zip(current_ratios, current_prices, symbols))
    zipped.sort(reverse=True)
    print("\n", zipped)


# analyze_symbols(get_good_symbols(), 2)

iter_count = 1
while True:
    start_whole = time.perf_counter()
    start_full_list = time.perf_counter()
    master_list, xtse_symbols, xnas_symbols, xnyse_symbols = get_symbols(symbol_count)
    stop_full_list = time.perf_counter()
    start_analyze = time.perf_counter()
    analyze_symbols(master_list, iter_count)
    stop_analyze = time.perf_counter()
    start_analyze_good = time.perf_counter()
    analyze_good_symbols(get_good_symbols())
    stop_analyze_good = time.perf_counter()
    # 43200s == 12h
    time.sleep(60)
    start_analyze2 = time.perf_counter()
    analyze_symbols(get_good_symbols(), iter_count)
    stop_analyze2 = time.perf_counter()
    start_analyze_good2 = time.perf_counter()
    analyze_good_symbols(get_good_symbols())
    stop_analyze_good2 = time.perf_counter()
    time.sleep(60)
    stop_whole = time.perf_counter()
    print("\n---------------------------------------")
    print(f"\nTimer Info for iteration {iter_count}")
    print(f"Master List: {round(stop_full_list - start_full_list, 2)}s\n"
          f"Analyze Full: {round(stop_analyze - start_analyze, 2)}s\n"
          f"Alternate Analyze Good: {round(stop_analyze_good - start_analyze_good, 2)}s\n"
          f"Analyze Good: {round(stop_analyze2 - start_analyze2, 2)}s\n"
          f"Alternate Analyze Good 2: {round(stop_analyze_good2 - start_analyze_good2, 2)}s\n")
    print("---------------------------------------\n")
    iter_count += 1
