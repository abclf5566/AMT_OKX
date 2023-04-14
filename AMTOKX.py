import json
import time
import okx.Account as Account
import okx.Trade as Trade
import math
import okx.PublicData as Public
from quart import Quart, request
import hupper

with open("accinfo.json", "r") as f:
    data = json.load(f)

api_key = data["api_key"]
secret_key = data["secret_key"]
passphrase = data["passphrase"]
flag = '0'

accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
publicAPI = Public.PublicAPI(api_key, secret_key, passphrase, False, flag)

app = Quart(__name__)

instrument_id = 'ETH-USDT-SWAP'

ticker = publicAPI.get_instruments(instType='SWAP', instId=instrument_id)
lot_size = float(ticker['data'][0]['lotSz'])

open_long_order_id = None
open_short_order_id = None

@app.route('/webhook', methods=['POST'])
async def webhook():
    global open_long_order_id
    global open_short_order_id

    data = await request.get_json()
    entry_price = float(data['price'])
    direction = data['direction']
    if direction == "test" or direction == "TEST":
        return{
            'code': 0,
            'message':'Test donn!'
        }
    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='cross')

    accounts = accountAPI.get_account_balance()
    for item in accounts['data'][0]['details']:
        if item['ccy'] == 'USDT':
            usdt_balance = float(item['availBal'])
            break

    rounded_usdt_balance = math.floor(usdt_balance)

    side = None
    if direction == "Long Entry":
        side = 'buy'
    elif direction == "Short Entry":
        side = 'sell'
    elif direction == "Close Long Entry":
        close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="cross")
        side = 'sell'
        print(f"Closed long position: {close_order}")
        open_long_order_id = None
        return {
            'code': 200,
            'message': 'OK'
        }
    elif direction == "Close Short Entry":
        close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="cross")
        side = 'buy'
        print(f"Closed short position: {close_order}")
        open_short_order_id = None
        return {
            'code': 200,
            'message': 'OK'
        }
    
    # 先检查是否有多头仓位，如果有则平掉
    positions = accountAPI.get_positions(instId=instrument_id)
    long_position = None
    short_position = None

    for position in positions['data']:
        if position['side'] == 'long':
            long_position = position
        elif position['side'] == 'short':
            short_position = position

    # 如果有多头仓位且信号为做空，先平掉多头仓位
    if long_position and direction == "Short Entry":
        close_long_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="cross")
        print(f"Closed long position: {close_long_order}")    

    if direction == "Long Entry" or direction == "Short Entry":
        order = tradeAPI.place_order(
            instId=instrument_id,
            tdMode='cross',
            side=side,
            ordType='limit',
            px=entry_price,
            sz=1
        )

        if direction == "Long Entry":
            open_long_order_id = order['data'][0]['ordId']
        elif direction == "Short Entry":
            open_short_order_id = order['data'][0]['ordId']

        print(order)

        return {
            'code': 200,
            'message': 'OK'
        }
    
    else:
        return {
            'code': 400,
            'message': 'Invalid direction'
        }

if __name__ == '__main__':
    reloader = hupper.start_reloader(f'{__name__}:app.run')
    reloader.run(host='0.0.0.0', port=8080)
