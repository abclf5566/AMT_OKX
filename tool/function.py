# tool/function.py

import asyncio

def get_precision(public_api, inst_id):
    inst_info = public_api.get_instruments(instType="SWAP")
    for inst in inst_info['data']:
        if inst['instId'] == inst_id:
            tick_sz = inst['tickSz']
            if '.' in tick_sz:
                return len(tick_sz.split('.')[1])
            else:
                return 0
    return None

async def close_position(instrument_id, tradeAPI):
    close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
    print(f"Closed position: {close_order}")
    await wait_for_close_order(tradeAPI, instrument_id, close_order['data'][0]['ordId'])
    return close_order

async def wait_for_close_order(tradeAPI, instrument_id, ordId):
    while True:
        order_info = tradeAPI.get_order(instId=instrument_id, ordId=ordId)
        if order_info['data'][0]['state'] == 'filled':
            break
        await asyncio.sleep(1)  # 等待1秒再次檢查訂單狀態
        
def get_message_code(data, code):
    for msg in data['message']:
        if code in msg:
            return msg[code]
    return None