import re
import time

import yahooquery
from openpyxl import load_workbook

from stonk_functions import RecentlyUpdated, stock_stats, is_float, JustSkip, get_dcf_npv, get_roe_npv
from stonk_list import DB_FILE_PATH, create_connection


def update_good_spreadsheets(good_symbols):
    print("Updating individual 'good' spreadsheets")
    template_file = "Stonks Files\\Individual Good Symbol Spreadsheets\\!Individual Good Symbol Template.xlsx"
    good_symbols_to_update = []
    for symbol in good_symbols:
        try:
            conn = create_connection(DB_FILE_PATH)
            with conn:
                cur = conn.cursor()
                sql = "SELECT last_updated FROM stonks WHERE symbol=?"
                cur.execute(sql, (symbol,))
                last_updated = cur.fetchall()
            if last_updated:
                updated_time = last_updated[0][0]
                if abs(int(time.time()) - updated_time) / 1000 > 86400 / 2:  # 86400s = 24h
                    good_symbols_to_update.append(symbol)
        except (KeyError, ValueError):
            pass
    yahoo_symbols = []
    for x, symbol in enumerate(good_symbols_to_update):
        if ".to" in symbol or ".cn" in symbol:
            yahoo_symbols.append(symbol.upper())
        else:
            yahoo_symbols.append(symbol.split(".")[0])
    print("Waiting on yahoo to return stock info")
    good_tickers = yahooquery.Ticker(yahoo_symbols)
    good_recommendations = good_tickers.recommendations
    good_tickers = good_tickers.all_modules
    print("Stock info received.")
    total_symbols = len(good_symbols_to_update)
    for x, symbol in enumerate(good_symbols_to_update):
        conn = create_connection(DB_FILE_PATH)
        with conn:
            cur = conn.cursor()
            sql = "SELECT title FROM stonks WHERE symbol=?"
            cur.execute(sql, (symbol,))
            title = cur.fetchall()[0]
            file_title = str(title).strip().replace(' ', '_')
            file_title = re.sub(r'(?u)[^-\w.]', '', file_title)
            file_save = "Stonks Files\\Individual Good Symbol Spreadsheets\\" + symbol.split(".")[0] + " - " + \
                        file_title + ".xlsx"

        try:
            prev_wb = load_workbook(file_save)
            updated_time = int(prev_wb["Stats"].cell(1, 5).value)
            if abs(int(time.time()) - updated_time) < (86400 / 2):  # 86400/2 s = 12h
                raise RecentlyUpdated
        except (FileNotFoundError, TypeError):
            pass

        recently_updated = False
        print(f"{x}/{total_symbols} - {symbol}")
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
            retrieve_stonk_data = False
            try:
                conn = create_connection(DB_FILE_PATH)
                with conn:
                    cur = conn.cursor()
                    sql = "SELECT * FROM stonks WHERE symbol=?"
                    cur.execute(sql, (symbol,))
                    db_stonk_results = cur.fetchall()
                    title = db_stonk_results[8]
                    industry = db_stonk_results[9]
                    current_price = db_stonk_results[2]
                    summary = db_stonk_results[18]
                    esg_score = db_stonk_results[16]
                    controversy_level = db_stonk_results[17]
                    market_cap = db_stonk_results[10]
                    revenue = db_stonk_results[11]
                    quarterly_assets = db_stonk_results[13]
                    quarterly_liabilities = db_stonk_results[14]
                    long_term_debt = db_stonk_results[15]
                    net_income = db_stonk_results[12]
                    current_10y_backtrack_dcf = db_stonk_results[4]
            except (TypeError, ValueError, KeyError) as e:
                print(e)
                retrieve_stonk_data = True
                pass
            if retrieve_stonk_data:
                title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, net_income, \
                revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, liabilities_raw, \
                fcf_raw_value, shares_outstanding_raw, stockholders_equity_raw, historical_ROE, \
                trailing_dividend_rate_raw, _ \
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
            wb = load_workbook(template_file)
            stonks_ws = wb["Stats"]
            stonks_ws.cell(1, 5).value = time.time()
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
            wb.save(file_save)
            wb.close()
        except (KeyError, ValueError, TypeError, JustSkip) as e:
            print(e)
            continue
        except RecentlyUpdated:
            print(f"{symbol} has been recently updated. Skipping excel sheet processing.")
            continue
        if not recently_updated:
            try:
                wb = load_workbook(file_save)
                stonks_ws = wb["Stats"]
                recommended = good_recommendations[yahoo_symbols[x]]['recommendedSymbols']
                recommended = [item["symbol"] for item in recommended]
                row = 8
                for recommended_symbol in recommended:
                    try:
                        esg_score = ""
                        controversy_level = ""
                        summary = ""
                        discount_rate = 0.09

                        title, industry, current_price, quarterly_liabilities, quarterly_assets, long_term_debt, \
                        net_income, revenue, market_cap, growth_estimate, current_EPS, historical_PE, cash_raw_eq, \
                        liabilities_raw, cf_raw_value, shares_outstanding_raw, stockholders_equity_raw, \
                        historical_ROE, trailing_dividend_rate_raw, fcf_raw_value, _ = stock_stats(recommended_symbol)

                        # Calculations
                        if is_float(growth_estimate) and is_float(current_EPS) and is_float(historical_PE):
                            growth_safety_pe = growth_estimate * 0.75
                            future_5y_estimate_pe = float(current_EPS) * float(historical_PE) * \
                                                    ((1.0 + growth_safety_pe) ** 5)
                            current_5y_backtrack_pe = int(future_5y_estimate_pe / ((1.0 + discount_rate) ** 5))
                        else:
                            current_5y_backtrack_pe = 0

                        if is_float(growth_estimate) and is_float(cash_raw_eq) and is_float(liabilities_raw) and \
                                is_float(fcf_raw_value) and is_float(shares_outstanding_raw):
                            if int(shares_outstanding_raw) != 0:
                                current_10y_backtrack_dcf = int(
                                    get_dcf_npv(discount_rate, cash_raw_eq, liabilities_raw, fcf_raw_value,
                                                shares_outstanding_raw, growth_estimate, 0.25))
                            else:
                                current_10y_backtrack_dcf = 0
                        else:
                            current_10y_backtrack_dcf = 0

                        if is_float(growth_estimate) and is_float(stockholders_equity_raw) and is_float(
                                historical_ROE) and is_float(
                                shares_outstanding_raw) and \
                                is_float(trailing_dividend_rate_raw):
                            if int(shares_outstanding_raw) != 0:
                                current_10y_backtrack_roe = get_roe_npv(discount_rate, stockholders_equity_raw,
                                                                        historical_ROE / 100, shares_outstanding_raw,
                                                                        trailing_dividend_rate_raw, growth_estimate,
                                                                        0.25)
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
                wb.save(file_save)
                wb.close()
            except (KeyError, ValueError, TypeError) as e:
                print(e)
                wb.save(file_save)
                wb.close()
                continue
            try:
                if "News" in wb.sheetnames:
                    good_news = yahooquery.Ticker(yahoo_symbols[x])
                    good_news = good_news.news()
                    wb = load_workbook(file_save)
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
                    wb.save(file_save)
                    wb.close()
            except (KeyError, ValueError, TypeError):
                wb.save(file_save)
                wb.close()
                pass


def update_spreadsheet(symbol_list):
    print("Updating 'good' spreadsheet")
    template_file = "Stonks Files\\Overall Good Symbol Spreadsheets\\Overall Good Symbols Template.xlsx"
    file_save = "Stonks Files\\Overall Good Symbol Spreadsheets\\Stonks Data - " + \
                time.strftime("%Y-%b-%d -- %I %M %p") + ".xlsx"
    # with open('Stonks Files\\Output\\stock_data.txt') as json_file:
    #     stonks = json.load(json_file)
    wb = load_workbook(template_file)
    stonks_ws = wb.active
    row = 2
    total_symbols = len(symbol_list)
    for x, symbol in enumerate(symbol_list):
        print(f"{x}/{total_symbols} - {symbol}")
        try:
            conn = create_connection(DB_FILE_PATH)
            with conn:
                cur = conn.cursor()
                sql = "SELECT * FROM stonks WHERE symbol=?"
                cur.execute(sql, (symbol,))
                db_stonk_results = cur.fetchall()
                prefix = "B:\\Documents\\Programming\\Python\\Stonks\\Stonks Files" \
                         "\\Individual Good Symbol Spreadsheets\\"
                file_title = str(db_stonk_results[0][8]).strip().replace(' ', '_')
                file_title = re.sub(r'(?u)[^-\w.]', '', file_title)
                spreadsheet_link = prefix + symbol.split(".")[0] + " - " + file_title + ".xlsx"
                stonks_ws.cell(row, 1).hyperlink = spreadsheet_link
                stonks_ws.cell(row, 1).value = symbol
                stonks_ws.cell(row, 2).value = db_stonk_results[0][8]
                stonks_ws.cell(row, 3).value = db_stonk_results[0][7]
                stonks_ws.cell(row, 4).value = db_stonk_results[0][9]
                stonks_ws.cell(row, 5).value = db_stonk_results[0][2]
                stonks_ws.cell(row, 6).value = db_stonk_results[0][3]
                stonks_ws.cell(row, 7).value = db_stonk_results[0][4]
                stonks_ws.cell(row, 8).value = db_stonk_results[0][5]
                stonks_ws.cell(row, 10).value = db_stonk_results[0][10]
                stonks_ws.cell(row, 11).value = db_stonk_results[0][11]
                stonks_ws.cell(row, 12).value = db_stonk_results[0][12]
                stonks_ws.cell(row, 13).value = db_stonk_results[0][13]
                stonks_ws.cell(row, 14).value = db_stonk_results[0][14]
                stonks_ws.cell(row, 16).value = db_stonk_results[0][15]
                stonks_ws.cell(row, 18).value = db_stonk_results[0][16]
                stonks_ws.cell(row, 19).value = db_stonk_results[0][17]
                stonks_ws.cell(row, 20).value = db_stonk_results[0][18]
                row += 1
        except KeyError:
            continue
# current_prices, current_ratios, symbols = lowest_price(good_symbols=good_symbols)
    # zipped = list(zip(current_ratios, current_prices, symbols))
    # zipped.sort(reverse=True)
    # print("\n", zipped)
    wb.save(file_save)
    wb.close()
