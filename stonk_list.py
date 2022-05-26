import random
import sqlite3
from sqlite3 import Error

DB_FILE_PATH = r"sqlite\stonks.db"


##################
# DATABASE RETURN
#  0 - id
#  1 - symbol
#  2 - current
#  3 - pe
#  4 - dcf
#  5 - roe
#  6 - exchange
#  7 - quality
#  8 - title
#  9 - industry
# 10 - market_cap
# 11 - revenue
# 12 - net_income
# 13 - assets
# 14 - liabilities
# 15 - debt
# 16 - esg_score
# 17 - controversy
# 18 - summary
# 19 - last_updated
####################


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # print(sqlite3.version)
    except Error as e:
        print(e)

    return conn


def data_update(symbol, values):
    current, pe, dcf, roe, exchange, quality, title, industry, market_cap, revenue, \
    net_income, assets, liabilities, debt, esg_score, controversy, summary, last_updated = values
    try:
        conn = create_connection(DB_FILE_PATH)
        insert_sql_exists = ''' UPDATE stonks SET current=?, pe=?, dcf=?, roe=?, exchange=?, quality=?, title=?,
        industry=?, market_cap=?, revenue=?, net_income=?, assets=?, liabilities=?, debt=?, esg_score=?, 
        controversy=?, summary=?, last_updated=? WHERE symbol=? '''
        insert_sql_not_exists = ''' INSERT INTO stonks(current,pe,dcf,roe,exchange,quality,title,industry,market_cap,
        revenue,net_income,assets,liabilities,debt,esg_score,controversy,summary,last_updated) 
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
        select_sql = "SELECT * FROM stonks WHERE symbol=?"
        with conn:
            cur = conn.cursor()
            cur.execute(select_sql, (symbol,))
            query_results = cur.fetchall()
            # If the symbol is already in there just update the existing data.
            # If its not in there then insert a new row
            if query_results:
                cur = conn.cursor()
                cur.execute(insert_sql_exists, (current, pe, dcf, roe, exchange, quality, title, industry, market_cap,
                                                revenue, net_income, assets, liabilities, debt, esg_score, controversy,
                                                summary, last_updated, symbol))
            else:
                cur = conn.cursor()
                cur.execute(insert_sql_not_exists, (symbol, current, pe, dcf, roe, exchange, quality, title, industry,
                                                    market_cap, revenue, net_income, assets, liabilities, debt,
                                                    esg_score, controversy, summary, last_updated))
    except Exception as e:
        print(e)
        pass


def get_good_symbols(quality="okay"):
    try:
        conn = create_connection(DB_FILE_PATH)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM stonks")
            db_stonks_return = cur.fetchall()
    except (OSError, ValueError):
        pass

    good_symbols = []
    for db_row_return in db_stonks_return:
        try:
            if quality == "okay":
                if db_row_return[7] != "Bad":
                    good_symbols.append(db_row_return[1])
            else:
                if db_row_return[7] == "Good":
                    good_symbols.append(db_row_return[1])
        except (KeyError, ValueError):
            pass
    return good_symbols


def get_symbols(local_exchange_list, rand_value=0, return_bad=False):
    """
    Used to get the symbols.\n
    :param return_bad: Bool to include bad symbols in return list
    :param local_exchange_list: List of exchanges. Used for opening files.
    :param rand_value: Number of random symbols to return. Mainly used for testing. Default to 0 to ignore.
    :return: List of symbols
    """

    old_removed_symbols = []
    conn = create_connection(DB_FILE_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stonks")
        db_stonks_return = cur.fetchall()
    for db_row_return in db_stonks_return:
        try:
            if db_row_return[7] == "Bad":
                old_removed_symbols.append(db_row_return[1])
        except ValueError:
            old_removed_symbols.append(db_row_return[1])
            pass

    master_list = []
    prefix = "Stonks Files\\Input\\"
    for file_name in local_exchange_list:
        with open(file_name.format(prefix, "file"), "r") as file:
            lines = file.readlines()
        lines = [item.replace("\n", "") for item in lines if item.replace("\n", "") != ""]
        conn = create_connection(DB_FILE_PATH)
        with conn:
            for symbol in lines:
                cur = conn.cursor()
                sql = '''INSERT INTO symbols(symbol) SELECT(?) WHERE NOT EXISTS 
                (SELECT symbol FROM symbols WHERE symbol=?)'''
                cur.execute(sql, (symbol, symbol))

    conn = create_connection(DB_FILE_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM symbols")
        symbol_return = cur.fetchall()
    if return_bad:
        master_list = [symbol[0] for symbol in symbol_return]
    else:
        master_list = [symbol[0] for symbol in symbol_return if symbol not in old_removed_symbols]
    print(len(master_list))

    # Really only used for testing. Instead of returning the full list to analyze. Returns "rand_value"
    # number of symbols to analyze.
    if rand_value != 0:
        print(f"Choosing {rand_value} random symbols from Master List")
        chosen_numbers = []
        new_symbols = []
        while len(chosen_numbers) < rand_value:
            rand_int = random.randint(0, len(master_list) - 1)
            if rand_value not in chosen_numbers:
                chosen_numbers.append(rand_int)
                new_symbols.append(master_list[rand_int])
        master_list = new_symbols

    print(f"Master List is {len(master_list)} symbols")
    return master_list
