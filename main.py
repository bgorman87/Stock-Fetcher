import time

from stonk_functions import analyze_symbols
from stonk_list import get_symbols, get_good_symbols
from stonk_spreadsheets import update_good_spreadsheets, update_spreadsheet

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

exchange_list = ["{}tsx_{}.txt", "{}xnas_{}.txt", "{}xnyse_{}.txt", "{}cse_{}.txt"]
exchange_names_list = ["tsx", "xnas", "xnyse", "cse"]

rand_value = 3
iter_count = 1
while True:

    master_list = get_symbols(exchange_list, exchange_names_list, rand_value=rand_value)
    analyze_symbols(master_list, iter_count)
    update_good_spreadsheets(get_good_symbols())
    update_spreadsheet(get_good_symbols("okay"))

    # Un-necessary to check everytime, check every 3rd iteration
    if iter_count == 1 or iter_count % 3 == 0:
        master_list_removed = get_symbols(exchange_list, exchange_names_list, return_bad=True, rand_value=rand_value)
        analyze_symbols(master_list_removed, iter_count)

    # Once every thing is done, sleep for 12 hours
    if iter_count > 2:
        time.sleep(43200/2)

    iter_count += 1
