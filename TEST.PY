import json
import okx.Account as Account
import okx.Trade as Trade
import okx.PublicData as Public
from quart import Quart, request
import hupper

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


    
trade_size = accountAPI.get_max_order_size(instId=instrument_id,tdMode='isolated')
max_buy = trade_size["data"][0]["maxBuy"]
print(max_buy)