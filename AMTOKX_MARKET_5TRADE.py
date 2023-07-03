import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request
import tool.function as fn
from collections import defaultdict

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
instrument_ids = {
    'OKX:SOLUSDT.P': 'SOL-USDT-SWAP',
    'OKX:AAVEUSDT.P': 'AAVE-USDT-SWAP',
    'OKX:AVAXUSDT.P': 'AVAX-USDT-SWAP',
    'OKX:FTMUSDT.P': 'FTM-USDT-SWAP',
    'OKX:CRVUSDT.P': 'CRV-USDT-SWAP'
}

# 初始化交易信息字典
trade_info = defaultdict(dict)

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

    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='isolated')

    side = None
    if direction == "Long Entry":
        side = 'buy'
    elif direction == "Short Entry":
        side = 'sell'

    # 在處理新信號之前檢查當前持倉
    positions = accountAPI.get_positions(instId=instrument_id)
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
        if symbol in trade_info:
            await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position)
            trade_info[symbol].clear()

    if direction == "Exit":
        await close_positions()
        return {'code': 201, 'message': "Order EXIT DONE for " + symbol}
        
    await close_positions()


    # Get the list of open positions for the specified instruments
    positions = [accountAPI.get_positions(instId=instrument_id) for instrument_id in instrument_ids.values()]
    open_positions = [p for p in positions if p['data']]

    # Calculate the number of available trading pairs
    available_pairs = 5 - len(open_positions)

    # Get the max balance
    max_balance = accountAPI.get_max_balance()

    # Calculate the order size
    order_size = max_balance / available_pairs

    # Loop through each trading pair
    for instrument_id in instrument_ids.values():
        # Get the max buy for the trading pair
        trade_size = accountAPI.get_max_order_size(instId=instrument_id, tdMode='isolated')
        max_buy = trade_size["data"][0]["maxBuy"]

        # Adjust max_buy by a decreasing percentage until the order is successful
        for i, percentage in enumerate([1, 0.975, 0.95, 0.925, 0.9], 1):
            adjusted_max_buy = str(int(min(float(max_buy) * percentage, order_size)))  # Convert to int as sz only accepts integers
            order = tradeAPI.place_order(
                instId=instrument_id,
                tdMode='isolated',
                side=side,  # 使用 side 變數
                ordType='market',
                sz=adjusted_max_buy
            )
            if order['code'] == '0':
                break
            elif i == 5:  # If it's the last attempt
                raise Exception('Failed to place order after 5 attempts')

    trade_info[symbol]["order_id"] = order['data'][0]['ordId']
    trade_info[symbol]["direction"] = direction

    print(order)

    return {'code': 202, 'message': "Long Entry / Short Entry DONE"}

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8080)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        print("Shutting down the server gracefully...")
    except (ConnectionError, TimeoutError) as e:
        print(f"Connection or timeout error: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
