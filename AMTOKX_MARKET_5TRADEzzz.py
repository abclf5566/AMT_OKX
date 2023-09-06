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


# Your existing code up to the point where you handle the positions
# ...

    # Check if symbol already exists in trade_info
    if symbol in trade_info:
        current_direction = trade_info[symbol].get("direction", None)
        # Check if the current trade direction is the same as the new one
        if current_direction == direction:
            return {'code': 200, 'message': 'No action required. Trade direction is the same.'}
        else:
            # Close the existing position if the new direction is different
            close_result = await close_positions()
            if close_result is not None:
                return close_result
            
            # Place a new order in the opposite direction
            await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
            return {'code': 202, 'message': f"Order placed in opposite direction for {symbol}"}
    else:
        # If the symbol does not exist in trade_info, place a new order
        await fn.place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction, trade_info_lock)
        return {'code': 202, 'message': f"New order placed for {symbol}"}
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
