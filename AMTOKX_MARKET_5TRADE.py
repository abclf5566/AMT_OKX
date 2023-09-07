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

# 初始化交易信息字典和異步鎖
trade_info = defaultdict(dict)
trade_info_lock = asyncio.Lock()

app = Quart(__name__)

# Set leverage at the start of the program
for instrument_id in instrument_ids.values():
    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='isolated')

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = await request.get_json()
    if data is None:
        return {'code': 400, 'message': "Bad Request: Invalid JSON data"}

    direction = data['direction']

    #Get position from Webhook
    if direction == "Position":
        await fn.initialize_trade_info(instrument_ids, accountAPI, trade_info)
        if not trade_info:
            return {'code': 200, 'message': "目前沒有持倉"}
        else:
            position_messages = []
            for inst_id, info in trade_info.items():
                if info['direction'] not in ["Long Entry", "Short Entry"]:
                    continue  # skip entries with incorrect direction
                # Additional checks to ensure the information is valid
                if 'order_id' in info and info['order_id']:
                    msg = f"交易對:{inst_id} 交易編號:{info['order_id']} 倉位方向:{info['direction']}"
                    position_messages.append(msg)
            if not position_messages:
                return {'code': 200, 'message': "目前沒有有效的持倉"}
            formatted_message = " | ".join(position_messages)
            return {'code': 200, 'message': formatted_message}

    try:
        symbol = data['symbol']
    except KeyError:
        print('Bad Request: Invalid symbol. Need symbol')
        symbol = None  # Assign None only in case of an exception

    if symbol is None or symbol not in instrument_ids:
        return {'code': 400, 'message': f"Bad Request: Invalid symbol {symbol}"}

    instrument_id = instrument_ids[symbol]
    side = 'buy' if direction == "Long Entry" else 'sell'

    # Retrieve existing position information from trade_info
    current_trade_info = trade_info.get(symbol, {})
    long_position = current_trade_info.get("Long Entry", None)
    short_position = current_trade_info.get("Short Entry", None)

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

    # 如果信号方向与当前持仓方向相同，不执行任何操作
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
        close_order_id = await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position, trade_info, instrument_ids, trade_info_lock)
        if close_order_id is None:
            return {'code': 500, 'message': f"Failed to close positions for symbol {symbol}"}

        # Update trade_info after a successful close operation
        for key in list(trade_info.keys()):  # Use list to avoid RuntimeError: dictionary changed size during iteration
            if trade_info[key].get('order_id') == close_order_id:
                del trade_info[key]
        return None  # Return None if the operation was successful

    if direction == "Exit":
        if symbol in trade_info:
            # 如果有持倉，進行平倉操作
            close_result = await close_positions()
            if close_result is not None:
                return close_result
            return {'code': 201, 'message': f"Order EXIT DONE for {symbol}"}
        else:
            # 如果没有持倉，不需要操作
            return {'code': 200, 'message': f"No position to exit for {symbol}"}

    if symbol in trade_info:
        current_direction = trade_info[symbol].get("direction", None)
        if current_direction:
            if current_direction == direction:  # 如果方向相同，不做操作
                return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}
            else:  # 如果方向不同，平倉然後反向下單
                close_result = await close_positions()
                if close_result is not None:
                    return close_result
                await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
        else:
            # 如果trade_info中没有這個交易對的方向信息，直接下單
            await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
    else:
        # 如果trade_info中没有這個交易對，直接下單
        await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)

    await asyncio.sleep(1)
    return {'code': 202, 'message': "Long Entry / Short Entry DONE"}

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(fn.initialize_trade_info(instrument_ids, accountAPI, trade_info))
        print(f"Position is {trade_info}")
        app.run(host='0.0.0.0', port=25565)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        print("Shutting down the server gracefully...")
    except (ConnectionError, TimeoutError) as e:
        print(f"Connection or timeout error: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
