import json


print_bool = False


def data_update(symbol, stonk):
    try:
        with open('stock_data.txt') as json_file:
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
    with open('stock_data.txt', 'w') as outfile:
        json.dump(stonks, outfile, indent=4)


def add_good_symbol(symbol):
    skip_symbol = False
    if symbol:
        with open("good_symbols.txt", "r") as file:
            good_symbols_list = file.readlines()
        for line in good_symbols_list:
            if symbol in line:
                skip_symbol = True
                break
        if not skip_symbol:
            good_symbols_list.append(symbol)
            good_symbols_list = [item.replace("\n", "") for item in good_symbols_list]
            good_symbols_list = [item for item in good_symbols_list if item != ""]
            with open("good_symbols.txt", "w") as file:
                for good_symbol in good_symbols_list:
                    file.write(good_symbol + "\n")


def remove_symbol(removed_symbol=None, update_list=False, e=""):
    skip_remove = False
    with open("removed_symbols.txt", "r") as file:
        old_removed = file.readlines()
    if removed_symbol is not None:
        for line in old_removed:
            if removed_symbol == line.split(" : ")[0]:
                skip_remove = True
                break
    old_removed_symbols = [item.split(" : ")[0] for item in old_removed]
    old_removed_reasons = [item.split(" : ")[1] for item in old_removed]
    old_removed_symbols = [item.replace("\n", "") for item in old_removed_symbols if item.replace("\n", "") != ""]
    old_removed_reasons = [item.replace("\n", "") for item in old_removed_reasons if item.replace("\n", "") != ""]
    if removed_symbol is not None and not skip_remove:
        with open("removed_symbols.txt", "w") as file:
            old_removed_symbols.append(removed_symbol)
            old_removed_reasons.append(e)
            for i, symbol in enumerate(old_removed_symbols):
                file.write(symbol + " : " + old_removed_reasons[i] + "\n")
    if update_list:
        for file_name in ["tsx_list.txt", "xnas_list.txt", "xnyse_list.txt"]:
            print(f"Updating List : {file_name}")
            with open(file_name, "r") as file:
                old_list = file.readlines()
            old_list = [item.replace("\n", "") for item in old_list if item.replace("\n", "") != ""]
            with open(file_name, "w+") as file:
                for item in old_list:
                    if item not in old_removed_symbols:
                        file.write(item + "\n")
            print(f"{file_name} : List Updated")


def get_symbols():
    remove_symbol(update_list=True)
    with open("removed_symbols.txt", "r") as file:
        old_removed_symbols = file.readlines()
    old_removed_symbols = [item.split(" : ")[0].replace("\n", "") for item in old_removed_symbols if item != ""]
    xnas_symbols = []
    xtse_symbols = []
    xnyse_symbols = []
    for file_name_prefix in ["tsx", "xnas", "xnyse"]:
        file_name = file_name_prefix + "_file.txt"
        with open(file_name, "r") as file:
            lines = file.readlines()
        lines = [item.replace("\n", "") for item in lines if item.replace("\n", "") != ""]
        file_name = file_name_prefix + "_list.txt"
        with open(file_name, "w+") as file:
            for item in lines:
                if item not in old_removed_symbols:
                    file.write("\n" + item)
            if "tsx" in file_name_prefix:
                xtse_symbols = [line for line in lines if line not in old_removed_symbols]
            if "xnas" in file_name_prefix:
                xnas_symbols = [line for line in lines if line not in old_removed_symbols]
            if "xnyse" in file_name_prefix:
                xnyse_symbols = [line for line in lines if line not in old_removed_symbols]
    return xtse_symbols, xnas_symbols, xnyse_symbols
