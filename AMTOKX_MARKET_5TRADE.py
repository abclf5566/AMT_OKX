
import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request 
import tool.function as fn
from collections import defaultdict
import asyncio

with open("accinfo.json", "r") as f1, open('instrument_ids.json', 'r') as f2:
    data = json.load(f1)
    instrument_ids = json.load(f2)


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
command_queue = asyncio.Queue()

app = Quart(__name__)

# Set leverage at the start of the program
for instrument_id in instrument_ids.values():
    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='isolated')

async def process_queue():
    print("process_queue started")
    while True:
        print("Waiting for a command from the queue...")
        command = await command_queue.get()
        print(f"Received a command: {command}")
        try:
            print("Starting to process the command...")
            instrument_id = command['instrument_id']
            direction = command['direction']
            symbol = command['symbol'] 

            side = 'buy' if direction == "Long Entry" else 'sell'

            # 更新 trade_info
            await fn.initialize_trade_info(instrument_ids, accountAPI, trade_info, trade_info_lock, specific_instrument_id=instrument_id)
            
            current_trade_info = trade_info.get(instrument_id, {})

            if direction in ["Long Entry", "Short Entry"] and current_trade_info.get("direction") == direction:
                print('code: 200, message: 無需執行操作，持倉方向與信號相符')
                continue

            long_position = current_trade_info.get("Long Entry", None)
            short_position = current_trade_info.get("Short Entry", None)

            # 在收到 "Exit" 指令時

            if direction == "Exit":
                # 重新获取持仓信息
                positions = accountAPI.get_positions(instId=instrument_id)
                long_position = None
                short_position = None

                for position in positions['data']:
                    pos = float(position['pos'])
                    if pos > 0:
                        long_position = position
                    elif pos < 0:
                        short_position = position

                if long_position or short_position:  # 如果有持仓
                    await fn.close_position(instrument_id, tradeAPI)
                    
                    # 删除 trade_info 中的条目
                    async with trade_info_lock:
                        if instrument_id in trade_info:
                            del trade_info[instrument_id]
                            
                    print(f"Debug: Updated trade_info after Exit = {trade_info}")  # Debugging line


                    continue #{'code': 201, 'message': f"Order EXIT DONE for {symbol}"}
                else:  # 如果没有持仓
                    continue #{'code': 200, 'message': f"No position to exit for {symbol}"}


            # 如果 trade_info 中有這個交易對的方向信息
            current_direction = current_trade_info.get("direction", None)
            if current_direction:
                if current_direction != direction:  
                    # 如果方向不同，平倉然後反向下單
                    close_result = await fn.close_position(instrument_id, tradeAPI)
                    if close_result is not None:
                        print("Position closed successfully. Proceeding to place a new order.")
                    await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
                else:
                    print("Direction is the same, no action needed.")
            else:
                # 如果 trade_info 中没有這個交易對的方向信息，直接下單
                await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            print(trade_info)
            print("Command processing done.")
            command_queue.task_done()  #{'code': 202, 'message': "Long Entry / Short Entry DONE"}

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = await request.get_json()
    if data is None:
        return {'code': 400, 'message': "Bad Request: Invalid JSON data"}
    
    direction = data['direction']
    symbol = data.get('symbol', None)  # 使用 get 以防止 KeyError

    if symbol is None or symbol not in instrument_ids:
        return {'code': 400, 'message': f"Bad Request: Invalid symbol {symbol}"}

    instrument_id = instrument_ids[symbol]
    
    # 將指令、instrument_id 和 symbol 放入隊列
    await command_queue.put({'instrument_id': instrument_id, 'direction': direction, 'symbol': symbol})
    print(command_queue)
    return {'code': 202, 'message': "Command queued"}

@app.before_serving
async def startup():
    await fn.initialize_trade_info(instrument_ids, accountAPI, trade_info, trade_info_lock)
    print(f"Position is {trade_info}")
    asyncio.create_task(process_queue())  # 使用 asyncio.create_task 而不是 loop.create_task

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=25565)  # 沒有 loop=loop 參數
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        print("Shutting down the server gracefully...")
    except (ConnectionError, TimeoutError) as e:
        print(f"Connection or timeout error: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
