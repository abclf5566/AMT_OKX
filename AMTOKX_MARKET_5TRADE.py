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

    # 在處理新信號之前檢查當前持倉
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

    # 如果信號方向與當前持倉相同，不執行任何操作
    if direction == "Long Entry" and long_position is not None:
        # Update trade_info
        trade_info[symbol] = {"order_id": long_position['posId'], "direction": "Long Entry"}
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}
    elif direction == "Short Entry" and short_position is not None:
        # Update trade_info
        trade_info[symbol] = {"order_id": short_position['posId'], "direction": "Short Entry"}
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}


    # 修改close_positions函数
    async def close_positions():
        close_order_id = await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position, trade_info, instrument_ids)
        # 检查关闭操作是否成功
        if close_order_id is None:
            # 如果关闭操作失败，返回一个错误消息
            return {'code': 500, 'message': f"Failed to close positions for symbol {symbol}"}

        # Update trade_info after a successful close operation
        for key in list(trade_info.keys()):  # Use list to avoid RuntimeError: dictionary changed size during iteration
            if trade_info[key].get('order_id') == close_order_id:
                del trade_info[key]
        return None  # Return None if the operation was successful

    if direction == "Exit":
        close_result = await close_positions()
        if close_result is not None:
            # 如果关闭操作失败，返回错误消息
            return close_result
        return {'code': 201, 'message': "Order EXIT DONE for " + symbol}

    close_result = await close_positions()
    if close_result is not None:
        # 如果关闭操作失败，返回错误消息
        return close_result

    await close_positions()

    if direction in ["Long Entry", "Short Entry"]:
        close_result = await close_positions()
        if close_result is not None:
            # 如果关闭操作失败，返回错误消息
            return close_result
        await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids,symbol,direction)

    # Add a delay between each request
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
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")