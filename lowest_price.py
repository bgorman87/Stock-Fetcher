import json

with open("stock_data.txt", "r") as file:
    stonks = json.load(file)

with open("good_symbols.txt", "r") as file:
    good_symbols = file.readlines()

good_symbols = [item.replace("\n","") for item in good_symbols]
lowest_price = 1000.0
lowest_priced_symbol = ""

for good_symbol in good_symbols:
    if float(stonks[good_symbol]["Current"]) < lowest_price:
        lowest_price = stonks[good_symbol]["Current"]
        lowest_priced_symbol = good_symbol

print(f"{lowest_priced_symbol} is the lowest good symbol priced at: ${lowest_price}")