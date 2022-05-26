import time

from stonk_functions import analyze_symbols
from stonk_list import get_symbols, get_good_symbols
from stonk_spreadsheets import update_good_spreadsheets, update_spreadsheet


exchange_list = [
    "{}tsx_{}.txt", 
    "{}xnas_{}.txt", 
    "{}xnyse_{}.txt", 
    "{}cse_{}.txt"
    ]

rand_value = 0  # Set value to 0 to use all symbols
iter_count = 1  # Keep track of iterations
while True:
    # Get the master list of all symbols to be analyzed
    master_list = get_symbols(
        exchange_list, 
        rand_value=rand_value
        )
    
    # Anlyze the symbols from the list
    analyze_symbols(master_list, iter_count)
    
    # Update indivdual spreadsheets with analysis values
    update_good_spreadsheets(get_good_symbols())
    
    # Update overall spreadsheet which contains all values requested
    update_spreadsheet(get_good_symbols("okay"))

    # Sometimes a stocks values may have not been updated on the websites
    # or the connection failed so didnt return anything at all.
    # So instead of permanately writing "Bad" stocks off, 
    # re-check them every so often, like every 3rd iteration
    if iter_count == 1 or iter_count % 3 == 0:
        
        master_list_removed = get_symbols(
            exchange_list,
            return_bad=True, 
            rand_value=rand_value
            )
        
        analyze_symbols(master_list_removed, iter_count)

    # Sometimes I stop the program for a few days/weeks so run twice to make sure everything is updated
    # Once every thing is done, sleep for 12 hours
    if iter_count > 2:
        time.sleep(43200/2)

    iter_count += 1
