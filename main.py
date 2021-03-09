from stonk_functions import *
from stonk_list import *
import random

# TODO  - Save calculated values into json file.
#       - Possibly Chart/Graph Results
#       - Some sort of system to automatically import stock symbols into a master list
#       - Some sort of notification when PE/DCF/ROE is higher than the current stock price.
#           - In this notification, maybe list the industry and in future maybe some symbols the I can use to compare


class SkipStock(Exception):
    pass


class ExistingStock(Exception):
    pass


xtse_symbols, xnas_symbols, xnyse_symbols = get_symbols()
master_list = xtse_symbols + xnas_symbols + xnyse_symbols
print(len(master_list))
number = 0
if number != 0:
    print(f"Choosing {number} random symbols from Master List")
    chosen_numbers = []
    new_symbols = []
    while len(chosen_numbers) < number:
        rand_int = random.randint(0, len(master_list)-1)
        if number not in chosen_numbers:
            chosen_numbers.append(rand_int)
            new_symbols.append(master_list[rand_int])
    master_list = new_symbols
print(f"Master List is {len(master_list)} symbols")

print_bool = False
discount_rate = 0.09
growth_safety_pe = 0
future_5y_estimate_pe = 0
removed_symbols = []
good_symbols = []
skip_existing = True

for i, symbol in enumerate(master_list):
    historical_PE = ""
    historical_ROE = ""
    current_EPS = ""
    current_price = ""

    morningstar_symbol = symbol.split(".")[0]
    yahoo_symbol = symbol.split(".")[0]
    exchange = ""
    exchange_fmt = ""
    # Yahoo Finance needs .TO suffix for TSX
    #   But does not need a suffix for US stocks
    if ".tsx" in symbol:
        exchange = "tsx"
        exchange_fmt = "TSX"
        morningstar_symbol = "XTSE:" + symbol.split(".")[0]
        yahoo_symbol = symbol.split(".")[0] + ".TO"
    elif ".nas" in symbol:
        exchange = "xnas"
        exchange_fmt = "NASDAQ"
        morningstar_symbol = "XNAS:" + symbol.split(".")[0]
    elif ".nyse" in symbol:
        exchange = "xnyse"
        exchange_fmt = "NYSE"

    new_stonk = {"Exchange": "", "Current": 0, "P/E": 0, "DCF": 0, "ROE": 0}
    print(f"Analyzing {symbol.split('.')[0]} - {exchange_fmt} - {i+1}/{len(master_list)}")
    current_10y_backtrack_roe = 0
    current_10y_backtrack_dcf = 0
    current_5y_backtrack_pe = 0

    try:
        if skip_existing:
            with open('stock_data.txt', 'r') as json_file:
                stonks = json.load(json_file)
            try:
                temp = stonks[symbol]
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
        ceq_link = f"https://ca.finance.yahoo.com/quote/{yahoo_symbol}/balance-sheet?p={yahoo_symbol}"
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
                current_10y_backtrack_roe = get_roe_npv(discount_rate, stockholders_equity_raw, historical_ROE / 100,
                                                        shares_outstanding_raw,
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

        pe_update = True
        dcf_update = True
        roe_update = True

        print(symbol, " - ", title.replace("Analyst Ratings, Estimates & Forecasts - Yahoo Finance", ""))
        new_stonk["Exchange"] = exchange_fmt

        new_stonk["Current"] = current_price

        new_stonk["P/E"] = current_5y_backtrack_pe
        print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")

        new_stonk["DCF"] = current_10y_backtrack_dcf
        print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")

        new_stonk["ROE"] = current_10y_backtrack_roe
        print(f"Current Price Based on ROE 10y Estimate: ${current_10y_backtrack_roe}")

        if current_price < current_5y_backtrack_pe and current_price < current_10y_backtrack_dcf and current_price \
                < current_10y_backtrack_roe:
            print(symbol, ": Could be a good investment, added to good symbol list.")
            add_good_symbol(symbol)
        data_update(symbol, new_stonk)

        if print_bool:
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
