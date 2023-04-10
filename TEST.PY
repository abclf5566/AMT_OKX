import json
import time
from flask import Flask, request
import okx.Account as Account
import okx.Trade as Trade
import math
import okx.PublicData as Public



with open("accinfo.json", "r") as f:
    data = json.load(f)

api_key = data["api_key"]
secret_key = data["secret_key"]
passphrase = data["passphrase"]
flag = '0'

accountAPI = Account.AccountAPI(api_key, secret_key, passphrase,False, flag)
tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase,False, flag)

app = Flask(__name__)

instrument_id = 'ETH-USDT-SWAP'

# Add this global variable to store the order_id
open_order_id = None

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     global open_order_id  # Use the global variable open_order_id

#     data = request.get_json()
#     entry_price = float(data['price'])
#     direction = data['direction']

#     # Set leverage
#     accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='cross')

#     # Get account information
#     accounts = accountAPI.get_account_balance()
#     for item in accounts['data'][0]['details']:
#         if item['ccy'] == 'USDT':
#             usdt_balance = float(item['availBal'])
#             break

#     instrument_info = Public.PublicAPI()
#     asa=instrument_info.get_instruments(instType="SWAP",instId=instrument_id)
#     # Get the lot size from instrument_info
#     lot_size = float(asa['data'][0]['lotSz'])

#     # Calculate the order quantity
#     qty = math.floor((usdt_balance / entry_price) / lot_size) * lot_size

#     side = None
#     if direction == "Long Entry":
#         side = 'buy'
#     elif direction == "Short Entry":
#         side = 'sell'
#     elif direction == "Close Long Entry":
#         side = 'sell'
#         # Close the position using the open_order_id
#         close_order = tradeAPI.close_position(instId=instrument_id, ordId=open_order_id)
#         print(f"Closed long position: {close_order}")
#         return {
#             'code': 200,
#             'message': 'OK'
#         }
#     elif direction == "Close Short Entry":
#         side = 'buy'
#         # Close the position using the open_order_id
#         close_order = tradeAPI.close_position(instId=instrument_id, ordId=open_order_id)
#         print(f"Closed short position: {close_order}")
#         return {
#             'code': 200,
#             'message': 'OK'
#         }

#     if direction == "Long Entry" or direction == "Short Entry":
#         order = tradeAPI.place_order(
#             instId=instrument_id,
#             tdMode='cross',
#             side=side,
#             ordType='limit',
#             px=entry_price,
#             sz=qty
#         )

#         # Update the open_order_id with the order_id from the response
#         open_order_id = order['data'][0]['ordId']

#         print(order)

#         return {
#             'code': 200,
#             'message': 'OK'
#         }
#     else:
#         return {
#             'code': 400,
#             'message': 'Invalid direction'
#         }

    # Get account information

publicAPI = Public.PublicAPI(api_key, secret_key, passphrase, False, flag)

    # 获取交易对信息

# 获取交易对信息
instruments_info = publicAPI.get_instruments('SWAP')['data']
# for instrument in instruments_info:
#     if instrument['instId'] == instrument_id:
#         min_size = float(instrument['lotSz'])
#         break

accounts = accountAPI.get_account_balance()
for item in accounts['data'][0]['details']:
    if item['ccy'] == 'USDT':
        usdt_balance = float(item['availBal'])
        break

# Calculate the order size
# order_size = usdt_balance / min_size
# rounded_order_size = math.floor(order_size) * min_size
usdt_balance_rounded=math.floor(usdt_balance)
if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8080)
    print(usdt_balance_rounded)


