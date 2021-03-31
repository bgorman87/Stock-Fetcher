with open("Stonks Files\\Input\\cse_file.txt", "r") as file:
    lines = file.readlines()

symbols = [line.replace("\n", "").split(".")[0] for line in lines if len(line.split(".")) <= 1]

with open("Stonks Files\\Input\\cse_file.txt", "w") as file:
    for line in symbols:
        file.write(line + ".cn\n")
