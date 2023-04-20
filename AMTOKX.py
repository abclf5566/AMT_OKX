import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request
import hupper
from tool.function import get_precision


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
    price_precision = get_precision(publicAPI,instrument_id)
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
        if position['side'] == 'long':
            long_position = position
        elif position['side'] == 'short':
            short_position = position

    if long_position and direction == "Short Entry":
        close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
        print(f"Closed long position: {close_order}")
    elif short_position and direction == "Long Entry":
        close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
        print(f"Closed short position: {close_order}")
    elif direction == "Exit":
        if long_position:
            close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
            print(f"Closed long position: {close_order}")
        if short_position:
            close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
            print(f"Closed short position: {close_order}")
        return {
            'code': 200,
            'message': 'OK'
        }
    else:
        if not long_position and direction == "Long Entry" or not short_position and direction == "Short Entry":
            trade_size = accountAPI.get_max_order_size(instId=instrument_id,tdMode='isolated')
            max_buy = trade_size["data"][0]["maxBuy"]
            print(max_buy)

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

            return {
                'code': 200,
                'message': 'OK'
            }
        else:
            return {
                'code': 200,
                'message': 'No action taken, position direction matches signal'
            }

if __name__ == '__main__':
    reloader = hupper.start_reloader(f'{__name__}:app.run')
    reloader.run(host='0.0.0.0', port=8080)
