with open("removed_symbols.txt", "r") as file:
    lines = file.readlines()

symbols = [line.split(".")[0] for line in lines if len(line.split(".")) <= 2]

with open("tsx_file.txt", "w") as file:
    for line in symbols:
        file.write(line)
