from stonk_functions import *
from stonk_list import xnas_symbols, xtse_symbols


class SkipStock(Exception):
    pass


master_list = xnas_symbols + xtse_symbols
stonks = {}
discount_rate = 0.09
growth_safety_pe = 0
future_5y_estimate_pe = 0

for symbol in master_list:
    new_stonk = {symbol: {"Current": 0, "P/E": 0, "DCF": 0, "ROE": 0}}
    current_10y_backtrack_roe = 0
    current_10y_backtrack_dcf = 0
    current_5y_backtrack_pe = 0
    morningstar_symbol = symbol
    yahoo_symbol = symbol
    if symbol in xnas_symbols:
        morningstar_symbol = "XNAS:" + symbol
    elif symbol in xtse_symbols:
        morningstar_symbol = "XTSE:" + symbol
        yahoo_symbol = symbol + ".TO"
    try:
        ## Stock Scraping
        title = get_yahoo_stat(yahoo_symbol, "title")
        current_EPS, current_price = get_yahoo_stat(yahoo_symbol, "eps")
        historical_PE = get_morningstar_pe(morningstar_symbol)
        growth_estimate = get_yahoo_stat(yahoo_symbol, "growth")
        fcf_raw_value, fcf_fmt_value = get_yahoo_stat(yahoo_symbol, "fcf")
        historical_ROE = get_morningstar_roe(morningstar_symbol)
        cash_raw_eq, cash_fmt_eq, liabilities_raw, liabilities_fmt, stockholders_equity_raw, stockholders_equity_fmt = \
            get_yahoo_stat(yahoo_symbol, "ceq")
        shares_outstanding_raw, shares_outstanding_fmt, trailing_dividend_rate_raw, trailing_dividend_rate_fmt = \
            get_yahoo_stat(yahoo_symbol, "shares_outstanding")
        ## Calculations
        if not is_float(growth_estimate) and is_float(current_EPS) and is_float(historical_PE):
            growth_safety_pe = growth_estimate * 0.75
            future_5y_estimate_pe = float(current_EPS) * float(historical_PE) * ((1.0 + growth_safety_pe) ** 5)
            current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + 0.12) ** 5))
        elif not is_float(growth_estimate):
            print("Growth Estimate Not Found For:", symbol)
            raise SkipStock
        elif not is_float(current_EPS):
            print("Current EPS Not Found For:", symbol)
            raise SkipStock
        elif not is_float(historical_PE):
            print("Historical PE Ratio Not Found For:", symbol)
            raise SkipStock

        if not is_float(cash_raw_eq) and not is_float(liabilities_raw) and not is_float(fcf_raw_value) and not is_float(
                shares_outstanding_raw):
            current_10y_backtrack_dcf = int(
                get_dcf_npv(discount_rate, cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw,
                            growth_estimate, 0.25))
        elif not is_float(cash_raw_eq):
            print("Cash Equiv Not Found For:", symbol)
            raise SkipStock
        elif not is_float(liabilities_raw):
            print("Liabilities Not Found For:", symbol)
            raise SkipStock
        elif not is_float(fcf_raw_value):
            print("Free Cash Flow Not Found For:", symbol)
            raise SkipStock
        elif not is_float(shares_outstanding_raw):
            print("Shares Outstanding Not Found For:", symbol)
            raise SkipStock

        if not is_float(stockholders_equity_raw) and not is_float(historical_ROE) and not is_float(
                shares_outstanding_raw) and not is_float(trailing_dividend_rate_raw):
            current_10y_backtrack_roe = get_roe_npv(discount_rate, stockholders_equity_raw, historical_ROE / 100,
                                                    shares_outstanding_raw,
                                                    trailing_dividend_rate_raw, growth_estimate, 0.25)
        elif not is_float(stockholders_equity_raw):
            print("Stockholders Equity Not Found For:", symbol)
            raise SkipStock
        elif not is_float(historical_ROE):
            print("Historical ROE Not Found For:", symbol)
            raise SkipStock
        elif not is_float(trailing_dividend_rate_raw):
            print("Trailing Dividend Not Found For:", symbol)
            raise SkipStock
        new_stonk[symbol]["Current"] = current_price
        new_stonk[symbol]["P/E"] = current_5y_backtrack_pe
        new_stonk[symbol]["DCF"] = current_10y_backtrack_dcf
        new_stonk[symbol]["ROE"] = current_10y_backtrack_roe
        stonks.update(new_stonk)

        print(title)

        print("------ P/E CALC -----")
        print("Historical Price/Earnings:", historical_PE)
        print("Trailing EPS:", current_EPS)
        print(f"Growth Estimate: {growth_estimate * 100}%")
        print(f"Growth Safety Estimate: {growth_safety_pe * 100}%")
        print(f"Future 5y Price: ${int(future_5y_estimate_pe)}")
        print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")

        print("------ DCF CALC -----")
        print(f"Free Cash Flow: ${fcf_fmt_value}")
        print(f"Cash and Cash Equivalents: ${cash_fmt_eq}")
        print(f"Total Liabilities: ${liabilities_fmt}")
        print(f"Shares Outstanding: ${shares_outstanding_fmt}")
        print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")

        print("------ ROE CALC -----")
        print("Historical Return on Equity:", historical_ROE)
        print("Stockholders Equity:", stockholders_equity_fmt)
        print("Trailing Dividend Rate:", trailing_dividend_rate_fmt)
        print(f"Current Price Based on ROE 10y Estimate: ${current_10y_backtrack_roe}")

        print(stonks)
    except SkipStock:
        continue
