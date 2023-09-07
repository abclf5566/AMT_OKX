try:
    symbol = 'YA'
except KeyError:
    print('Bad Request: Invalid symbol. Need symbol')
    symbol = None  # Assign None only in case of an exception
print(symbol)