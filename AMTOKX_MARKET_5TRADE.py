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

    # 如果信號方向與當前持倉相同，不執行任何操作
    if direction == "Long Entry" and long_position is not None:
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}
    elif direction == "Short Entry" and short_position is not None:
        return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}

    # 修改close_positions函数
    async def close_positions():
        close_order_id = await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position, trade_info, instrument_ids)
        # 检查关闭操作是否成功
        if close_order_id is None:
            # 如果关闭操作失败，返回一个错误消息
            return {'code': 500, 'message': f"Failed to close positions for symbol {symbol}"}
        trade_info[symbol].clear()
    # 在"Exit"处理代码中，添加错误检查
    if direction == "Exit":
        close_result = await close_positions()
        if close_result is not None:
            # 如果关闭操作失败，返回错误消息
            return close_result
        return {'code': 201, 'message': "Order EXIT DONE for " + symbol}

    await close_positions()

    # 在这里，即使方向相同，也进行入场操作
    if direction in ["Long Entry", "Short Entry"]:
        # Update trade_info before placing order
        await fn.initialize_trade_info(instrument_ids, accountAPI, trade_info)

        # Count the number of trading pairs without positions
        no_position_count = sum(1 for inst_id in instrument_ids.values() if inst_id not in trade_info or trade_info[inst_id].get('order_id') is None)

        # Get the max buy for the trading pair
        trade_size = accountAPI.get_max_order_size(instId=instrument_id, tdMode='isolated')
        max_buy = trade_size["data"][0]["maxBuy"]

        # Adjust max_buy by a decreasing percentage until the order is successful
        for i, percentage in enumerate([1, 0.98, 0.96], 1):
            adjusted_max_buy = str(int(float(max_buy) * percentage / no_position_count))  # Convert to int as sz only accepts integers
            order = tradeAPI.place_order(
                instId=instrument_id,
                tdMode='isolated',
                side=side,  # 使用 side 變數
                ordType='market',
                sz=adjusted_max_buy
            )
            if order['code'] == '0':
                break
            elif i == 3:  # If it's the last attempt
                raise Exception('Failed to place order after 3 attempts')

        trade_info[symbol]["order_id"] = order['data'][0]['ordId']
        trade_info[symbol]["direction"] = direction

        print(order)
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