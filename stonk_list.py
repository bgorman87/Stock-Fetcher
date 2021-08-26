import json
import random

print_bool = False


def data_update(symbol, stonk):
    try:
        with open('Stonks Files\\Output\\stock_data.txt') as json_file:
            stonks = json.load(json_file)
    except (OSError, ValueError):
        stonks = {}
    try:
        _ = stonks[symbol]
    except KeyError:
        stonks[symbol] = {"Current": 0, "P/E": 0, "DCF": 0, "ROE": 0}

    if int(stonk["DCF"]) == int(stonks[symbol]["DCF"]):
        if print_bool:
            print("NPV DCF Not Changed")
    if int(stonk["P/E"]) == int(stonks[symbol]["P/E"]):
        if print_bool:
            print("NPV P/E Not Changed")
    if int(stonk["ROE"]) == int(stonks[symbol]["ROE"]):
        if print_bool:
            print("NPV ROE Not Changed")

    if stonk["P/E"] != 0 or stonk["DCF"] != 0 or stonk["ROE"] != 0:
        stonks[symbol].update(stonk)
    with open('Stonks Files\\Output\\stock_data.txt', 'w') as outfile:
        json.dump(stonks, outfile, indent=4)


def get_good_symbols(quality="okay"):
    try:
        with open('Stonks Files\\Output\\stock_data.txt') as json_file:
            stonks = json.load(json_file)
    except (OSError, ValueError):
        stonks = {}

    good_symbols = []
    for item, value in stonks.items():
        try:
            if quality == "okay":
                if value["Quality"] != "Bad":
                    good_symbols.append(item)
            else:
                if value["Quality"] == "Good":
                    good_symbols.append(item)
        except (KeyError, ValueError):
            pass
    return good_symbols


def get_symbols(local_exchange_list, local_exchange_names_list, rand_value=0, return_bad=False):
    """
    Used to get the symbols.\n
    :param return_bad: Bool to include bad symbols in return list
    :param local_exchange_list: List of exchanges. Used for opening files.
    :param local_exchange_names_list: List of exchange names. Used for opening files.
    :param rand_value: Number of random symbols to return. Mainly used for testing. Default to 0 to ignore.
    :return: List of symbols
    """

    # Why have two lists. Just use main stonk file.
    # remove_symbol(local_exchange_list, update_list=True)

    try:
        with open('Stonks Files\\Output\\stock_data.txt') as json_file:
            stonks = json.load(json_file)
    except (OSError, ValueError):
        stonks = {}

    old_removed_symbols = []
    for item, value in stonks.items():
        try:
            if value["Quality"] == "Bad":
                old_removed_symbols.append(item)
        except (KeyError, ValueError):
            old_removed_symbols.append(item)
            pass

    master_list = []
    prefix = "Stonks Files\\Input\\"
    for file_name in local_exchange_list:
        with open(file_name.format(prefix, "file"), "r") as file:
            lines = file.readlines()
        lines = [item.replace("\n", "") for item in lines if item.replace("\n", "") != ""]
        with open(file_name.format(prefix, "list"), "w+") as file:
            for item in lines:
                if item not in old_removed_symbols:
                    file.write("\n" + item)
        for exchange_name in local_exchange_names_list:
            if exchange_name in file_name:
                if return_bad:
                    master_list.extend([line for line in lines])
                else:
                    master_list.extend([line for line in lines if line not in old_removed_symbols])
    print(len(master_list))

    # Really only used for testing. Instead of returning the full list to analyze. Returns "rand_value"
    # number of symbols to analyze.
    number = rand_value
    if number != 0:
        print(f"Choosing {number} random symbols from Master List")
        chosen_numbers = []
        new_symbols = []
        while len(chosen_numbers) < number:
            rand_int = random.randint(0, len(master_list) - 1)
            if number not in chosen_numbers:
                chosen_numbers.append(rand_int)
                new_symbols.append(master_list[rand_int])
        master_list = new_symbols

    print(f"Master List is {len(master_list)} symbols")
    return master_list
