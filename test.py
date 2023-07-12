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


trade_size = accountAPI.get_max_order_size(instId=instrument_id,tdMode='isolated')
max_buy = trade_size["data"][0]["maxBuy"]
code_203 = data['message'][3]['code 200']
def aaa():
    if 3==3:
        return data['message'][3]['code 200']
    
if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8080)
    print(fn.get_message_code(data, 'code 200'))
