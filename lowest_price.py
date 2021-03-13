import json


def lowest_price(good_symbols):
    highest_ratio_current = 0
    with open("stock_data.txt", "r") as file:
        stonks = json.load(file)

    lowest_price_local = 1000.0
    lowest_priced_symbol = ""

    for good_symbol in good_symbols:
        if float(stonks[good_symbol]["Current"]) < lowest_price_local:
            lowest_price_local = stonks[good_symbol]["Current"]
            lowest_priced_symbol = good_symbol

    print(f"{lowest_priced_symbol} is the lowest good symbol priced at: ${lowest_price_local}")
    highest_ratio = 0
    lowest_value = 10000.0
    highest_ratio_symbol = []
    current_price_ratio = []
    current_ratio = []
    ratio_symbol = []
    for good_symbol in good_symbols:
        values = [stonks[good_symbol]["P/E"], stonks[good_symbol]["DCF"], stonks[good_symbol]["ROE"]]
        values = [value for value in values if value > 0]
        for item in values:
            if float(item) < lowest_value:
                lowest_value = float(item)
        current_price = float(stonks[good_symbol]["Current"])
        ratio = lowest_value/current_price
        current_price_ratio.append(current_price)
        current_ratio.append(ratio)
        ratio_symbol.append(good_symbol)
        if ratio > highest_ratio:
            highest_ratio = ratio
            highest_ratio_symbol = good_symbol
            highest_ratio_current = current_price
        # print(f"{good_symbol} has a ratio of {ratio}, with a current price of ${current_price}")
    print(f"{highest_ratio_symbol} has the highest ratio priced at: ${highest_ratio_current}, with a ratio of "
          f"{highest_ratio}")
    return ratio_symbol, current_ratio, current_price_ratio
