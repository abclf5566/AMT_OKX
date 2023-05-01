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
    if close_order['code'] == '51023':
        print('No position to close')
    elif close_order['code'] == '0':
        print('Position closed')
    else:
        print(f"Unexpected response: {close_order}")
    
    if close_order['data']:
        return {"code": close_order['code'], "instId": close_order['data'][0]['instId'], "posSide": close_order['data'][0]['posSide']}
    else:
        return {"code": close_order['code'], "instId": None, "posSide": None}
#need fix
async def wait_for_close_order(accountAPI, instId, posSide):
    if instId is None or posSide is None:
        return

    while True:
        orders = accountAPI.get_orders(instId=instId, state="live", posSide=posSide)
        if len(orders['data']) == 0:
            break
        else:
            await asyncio.sleep(1)


def get_message_code(data, code):
    for msg in data['message']:
        if code in msg:
            return msg[code]
    return None

async def close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position):
    if long_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed long position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])
    if short_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed short position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])

