import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request 
import tool.function as fn
from collections import defaultdict
import asyncio

with open("accinfo.json", "r") as f:
    data = json.load(f)
with open('instrument_ids.json', 'r') as f:
    instrument_ids = json.load(f)

api_key = data["api_key"]
secret_key = data["secret_key"]
passphrase = data["passphrase"]
flag = '0'

accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
publicAPI = Public.PublicAPI(api_key, secret_key, passphrase, False, flag)

# 初始化交易信息字典
trade_info = defaultdict(dict)

app = Quart(__name__)

# Set leverage at the start of the program
for instrument_id in instrument_ids.values():
    accountAPI.set_leverage(instId=instrument_id, lever=10, mgnMode='isolated')

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = await request.get_json()
    if data is None:
        return {'code': 400, 'message': "Bad Request: Invalid JSON data"}

    direction = data['direction']
    symbol = data['symbol']

    if symbol not in instrument_ids:
        return {'code': 400, 'message': f"Bad Request: Invalid symbol {symbol}"}

    instrument_id = instrument_ids[symbol]

    side = None
    if direction == "Long Entry":
        side = 'buy'
    elif direction == "Short Entry":
        side = 'sell'

    positions = accountAPI.get_positions(instId=instrument_id)
    print(f"Retrieved positions: {positions}")
    long_position = None
    short_position = None

    for position in positions['data']:
        pos = float(position['pos'])
        if pos > 0:
            long_position = position
        elif pos < 0:
            short_position = position
        await asyncio.sleep(0.2)

    if direction == "Long Entry" and long_position is not None:
        trade_info[symbol] = {"order_id": long_position['posId'], "direction": "Long Entry"}
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}
    elif direction == "Short Entry" and short_position is not None:
        trade_info[symbol] = {"order_id": short_position['posId'], "direction": "Short Entry"}
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}

    async def close_positions():
        close_order_id = await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position, trade_info, instrument_ids)
        if close_order_id is None:
            return {'code': 500, 'message': f"Failed to close positions for symbol {symbol}"}
        for key in list(trade_info.keys()):
            if trade_info[key].get('order_id') == close_order_id:
                del trade_info[key]
        return None

    if direction == "Exit":
        close_result = await close_positions()
        if close_result is not None:
            return close_result
        return {'code': 201, 'message': "Order EXIT DONE for " + symbol}

    close_result = await close_positions()
    if close_result is not None:
        return close_result

    if direction in ["Long Entry", "Short Entry"]:
        await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction)

    await asyncio.sleep(1)
    return {'code': 202, 'message': "Long Entry / Short Entry DONE"}


if __name__ == '__main__':
    try:
        asyncio.run(fn.initialize_trade_info(instrument_ids,accountAPI,trade_info))
        print(f"posiction is {trade_info}")
        app.run(host='0.0.0.0', port=25565)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        print("Shutting down the server gracefully...")
    except (ConnectionError, TimeoutError) as e:
        print(f"Connection or timeout error: {e}")