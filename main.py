import json
import re
import html5lib

import requests
from bs4 import BeautifulSoup


# How to determine when to buy stocks
# Multiple ways to determine intrinsic value of companies
# Calculate using various parameters what the stock price will be in the future.
# From this price, convert back to today's dollar value
# Calculate each methods price and compare to see if a stock is worth it
# e-book read? False

# It is better to be roughly right, than precisely wrong

# Use conservative values, with large margin of safety
# The lower the discount rate, the higher the safety factor (10% is a good value to start with)

# Create a dictionary with each stock symbol as key and another dictionary of required values as the key value

# TODO - Consolidate queries as much as possible to reduce risk of being blocked by yahoo finance

def get_dcf_npv(cash_and_cash_eq, liabilities, free_cash_flow, outstanding_shares, growth_rate, margin_of_safety):
    conservative_growth = growth_rate * (1-margin_of_safety)
    growth_decline = 0.05
    discount_rate = 0.09
    free_cash_growth = []
    npv_free_cash = []
    free_cash_growth.append(free_cash_flow * (1 + conservative_growth))
    npv_free_cash.append(free_cash_growth[0] / (1 + discount_rate))
    for i in range(2, 11):
        free_cash_growth.append(free_cash_growth[i-2] * (1 + (conservative_growth * ((1 - growth_decline) ** (i - 1)))))
        npv_free_cash.append(free_cash_growth[i-1] / ((1 + discount_rate) ** i))

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
    except (ValueError, AttributeError) as e:
        print(e)
    if values:
        return values[3][3]
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
    except (ValueError, AttributeError) as e:
        print(e)
    if content_rows:
        values = [float(value.get_text()) for value in content_rows]
    if values:
        return sum(values[5:-1])/5
    else:
        return values


def get_yahoo_stat(local_symbol, stat_type=None):
    current_eps_link = "https://ca.finance.yahoo.com/quote/{}?p={}"
    growth_estimate_link = "https://ca.finance.yahoo.com/quote/{}/analysis?p={}"
    fcf_link = "https://ca.finance.yahoo.com/quote/{}/cash-flow?p={}"
    ceq_link = "https://ca.finance.yahoo.com/quote/{}/balance-sheet?p={}"
    shares_outstanding_link = "https://finance.yahoo.com/quote/{}/key-statistics?p={}"
    if stat_type == "eps":
        link = current_eps_link.format(local_symbol, local_symbol)
    elif stat_type == "growth" or stat_type == "title":
        link = growth_estimate_link.format(local_symbol, local_symbol)
    elif stat_type == "fcf":
        link = fcf_link.format(yahoo_symbol, yahoo_symbol)
    elif stat_type == "ceq" or stat_type == "liabilities":
        link = ceq_link.format(yahoo_symbol, yahoo_symbol)
    elif stat_type == "shares_outstanding":
        link = shares_outstanding_link.format(yahoo_symbol, yahoo_symbol)
    else:
        link = ""
    data = ""
    try:
        html_content = requests.get(link).text
        soup = BeautifulSoup(html_content, 'lxml')
        pattern = re.compile(r'\s--\sData\s--\s')
        script_data = soup.find('script', text=pattern).contents[0]
        start = script_data.find("context") - 2
        json_data = json.loads(script_data[start:-12])
        if stat_type == "eps":
            data = json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['defaultKeyStatistics'] \
                ['trailingEps']['raw']
        elif stat_type == "growth":
            data = \
            json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['earningsTrend']['trend'][4]['growth'][
                'raw']
        elif stat_type == "title":
            data = json_data['context']['dispatcher']['stores']['PageStore']['pageData']['title']
        elif stat_type == "fcf":
            data = [json_data['context']['dispatcher']['stores']['QuoteTimeSeriesStore']['timeSeries'][
                        'trailingFreeCashFlow'][0]['reportedValue']['raw'],
                    json_data['context']['dispatcher']['stores']['QuoteTimeSeriesStore']['timeSeries'][
                        'trailingFreeCashFlow'][0]['reportedValue']['fmt']]
        elif stat_type == "ceq":
            data = [json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['balanceSheetHistory'][
                        'balanceSheetStatements'][0]['cash']['raw'],
                    json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['balanceSheetHistory'][
                         'balanceSheetStatements'][0]['cash']['fmt']]
        elif stat_type == "liabilities":
            data = [json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['balanceSheetHistory'][
                        'balanceSheetStatements'][0]['totalLiab']['raw'],
                    json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['balanceSheetHistory'][
                        'balanceSheetStatements'][0]['totalLiab']['fmt']]
        elif stat_type == "shares_outstanding":
            data = [json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['defaultKeyStatistics'][
                        'sharesOutstanding']['raw'],
                    json_data['context']['dispatcher']['stores']['QuoteSummaryStore']['defaultKeyStatistics'][
                        'sharesOutstanding']['fmt']]
    except (ValueError, AttributeError) as e:
        print(e)
    return data


xnas_symbols = ["AAPL"]
xtse_symbols = []
master_list = xnas_symbols + xtse_symbols
stonks = {}

for symbol in master_list:
    new_stonk = {symbol: {"P/E": 0, "DCF": 0, "ROE": 0}}
    morningstar_symbol = symbol
    yahoo_symbol = symbol
    if symbol in xnas_symbols:
        morningstar_symbol = "XNAS:" + symbol
    elif symbol in xtse_symbols:
        morningstar_symbol = "XTSE:" + symbol
        yahoo_symbol = symbol + ".TO"

    title = get_yahoo_stat(yahoo_symbol, "title")
    print(title)

    # print("------ P/E CALC -----")
    #
    # historical_PE = get_morningstar_pe(morningstar_symbol)
    # print("Historical Price/Earnings:", historical_PE)
    #
    # current_EPS = get_yahoo_stat(yahoo_symbol, "eps")
    # print("Trailing EPS:", current_EPS)
    #
    # growth_estimate = get_yahoo_stat(yahoo_symbol, "growth")
    # print(f"Growth Estimate: {growth_estimate * 100}%")
    #
    # growth_safety_pe = growth_estimate * 0.75
    # print(f"Growth Safety Estimate: {growth_safety_pe * 100}%")
    #
    # future_5y_estimate_pe = float(current_EPS) * float(historical_PE) * ((1.0 + growth_safety_pe) ** 5)
    # print(f"Future 5y Price: ${int(future_5y_estimate_pe)}")
    #
    # current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + 0.09) ** 5))
    # print(f"Current Price Based on P/E 5y Estimate: ${current_5y_backtrack_pe}")
    # new_stonk[symbol]["P/E"] = current_5y_backtrack_pe
    # print(new_stonk)
    #
    # print("------ DCF CALC -----")
    #
    # fcf_raw_value, fcf_fmt_value = get_yahoo_stat(yahoo_symbol, "fcf")
    # print(f"Free Cash Flow: ${fcf_fmt_value}")
    #
    # cash_raw_eq, cash_fmt_eq = get_yahoo_stat(yahoo_symbol, "ceq")
    # print(f"Cash and Cash Equivalents: ${cash_fmt_eq}")
    #
    # liabilities_raw, liabilities_fmt = get_yahoo_stat(yahoo_symbol, "liabilities")
    # print(f"Total Liabilities: ${liabilities_fmt}")
    #
    # shares_outstanding_raw, shares_outstanding_fmt = get_yahoo_stat(yahoo_symbol, "shares_outstanding")
    # print(f"Shares Outstanding: ${shares_outstanding_fmt}")
    #
    # current_10y_backtrack_dcf = int(get_dcf_npv(cash_raw_eq, liabilities_raw, fcf_raw_value, shares_outstanding_raw,
    #                                        growth_estimate, 0.25))
    # print(f"Current Price Based on DCF 10y Estimate: ${current_10y_backtrack_dcf}")
    # new_stonk[symbol]["DCF"] = current_10y_backtrack_dcf
    # print(new_stonk)

    print("------ ROE CALC -----")

    historical_ROE = get_morningstar_roe(morningstar_symbol)
    print("Historical Return on Equity:", historical_ROE)


    # finn_company_url = 'https://finnhub.io/api/v1/stock/profile2?symbol={}&token={}'
    # finn_eps_url = 'https://finnhub.io/api/v1/calendar/earnings?symbol={}&token={}'
    # finn_garbage = "c0ont1v48v6rduk5n4jg"

    # finn_company_url_filled = finn_company_url.format(symbol, finn_garbage)
    # r = requests.get(finn_company_url_filled)
    # print(r.json())
    #
    # finn_eps_url_filled = finn_eps_url.format(symbol, finn_garbage)
    # r = requests.get(finn_eps_url_filled)
    # print(r.json())

# For each company, perform the calculations and find the optimal stock price for each company.
# Save these values in a file and dict.

# Each time its run, check the previous value and whichever price is more optimal (higher), save that one.

# If the current stock price is equal to or lower than the optimal price, notify myself the companies. Buy, buy, buy.
