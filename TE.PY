import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request
import tool.function as fn

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
    if data is None:
        return {'code': 400, 'message': "Bad Request: Invalid JSON data"}

    direction = data['direction']

    accountAPI.set_leverage(instId=instrument_id, lever=5, mgnMode='isolated')

    side = None
    if direction == "Long Entry":
        side = 'buy'
    elif direction == "Short Entry":
        side = 'sell'

    # # 在處理新信號之前檢查當前持倉
    # positions = accountAPI.get_positions(instId=instrument_id)
    # long_position = None
    # short_position = None

    # for position in positions['data']:
    #     pos = float(position['pos'])
    #     if pos > 0:
    #         long_position = position
    #     elif pos < 0:
    #         short_position = position

    # # 如果信號方向與當前持倉相同，不執行任何操作
    # if direction == "Long Entry" and long_position is not None:
    #     return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}
    # elif direction == "Short Entry" and short_position is not None:
    #     return {'code': 200, 'message': '無需執行操作，持倉方向與信號相符'}

    # async def close_positions():
    #     await fn.close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position)

    # if direction == "Exit":
    #     await close_positions()
    #     return {'code': 201, 'message': "Order EXIT DONE"}

    # # Check for existing orders
    # orders = tradeAPI.get_order_list(instId=instrument_id)
    
    # # Cancel all existing orders
    # if orders['data']:
    #     for order in orders['data']:
    #         tradeAPI.cancel_algo_order([{'algoId': order['algoId'], 'instId': instrument_id}])
    
    # await close_positions()

    trade_size = accountAPI.get_max_order_size(instId=instrument_id, tdMode='isolated')
    max_buy = trade_size["data"][0]["maxBuy"]

    order = tradeAPI.place_order(
        instId=instrument_id,
        tdMode='isolated',
        posSide=side,
        side=side,
        ordType='market',
        sz=max_buy
    )

    if direction == "Long Entry":
        open_long_order_id = order['data'][0]['ordId']
    elif direction == "Short Entry":
        open_short_order_id = order['data'][0]['ordId']

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
