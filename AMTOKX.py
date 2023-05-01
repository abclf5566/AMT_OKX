import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request
import tool.function as fn
import asyncio

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

instrument_id = 'AVAX-USDT-SWAP'

open_long_order_id = None
open_short_order_id = None

@app.route('/webhook', methods=['POST'])
async def webhook():
    
    global open_long_order_id
    global open_short_order_id

    data = await request.get_json()
    entry_price = float(data['price'])
    price_precision = fn.get_precision(publicAPI, instrument_id)
    if price_precision:
        entry_price = round(entry_price, price_precision)
    else:
        print("Error: Unable to get price precision.")
    direction = data['direction']

    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='isolated')

    side = None
    if direction == "Long Entry":
        side = 'buy'
    elif direction == "Short Entry":
        side = 'sell'

    positions = accountAPI.get_positions(instId=instrument_id)
    long_position = None
    short_position = None

    for position in positions['data']:
        pos = float(position['pos'])
        if pos > 0:
            long_position = position
        elif pos < 0:
            short_position = position

    async def close_positions():
        await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position)

    if direction == "Exit":
        await close_positions()
        return {'code': 201,'message': "Order EXIT DONE"}
    
    if long_position:
        close_order = await fn.close_position(instrument_id, tradeAPI)
        print(f"Closed long position: {close_order}")
        if close_order['code'] == '0':
            await fn.wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])

    if short_position:
        close_order = await fn.close_position(instrument_id, tradeAPI)
        print(f"Closed short position: {close_order}")
        if close_order['code'] == '0':
            await fn.wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])

    else:
        if not long_position and direction == "Long Entry" or not short_position and direction == "Short Entry":
            trade_size = accountAPI.get_max_order_size(instId=instrument_id,tdMode='isolated')
            max_buy = trade_size["data"][0]["maxBuy"]

            order = tradeAPI.place_order(
                instId=instrument_id,
                tdMode='isolated',
                side=side,
                ordType='limit',
                px=entry_price,
                sz=max_buy
            )

            if direction == "Long Entry":
                open_long_order_id = order['data'][0]['ordId']
            elif direction == "Short Entry":
                open_short_order_id = order['data'][0]['ordId']

            print(order)

            return {'code': 202,'message': "Long Entry / Short Entry DONE"}
        else:
            return {'code': 200,'message': "No action taken, position direction matches signal"}


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8080)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        print("Shutting down the server gracefully...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
