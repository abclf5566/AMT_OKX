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
    print(f"Closing position for {instrument_id}...")
    close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
    print(f"Received close order response: {close_order}")
    if close_order['code'] == '51023':
        print('No position to close')
    elif close_order['code'] == '0':
        print('Position closed')
    else:
        print(f"Unexpected response: {close_order}")
    
    if close_order['data']:
        if 'ordId' in close_order['data'][0]:
            return {"code": close_order['code'], "ordId": close_order['data'][0]['ordId'], "instId": instrument_id, "posSide": close_order['data'][0]['posSide']}
        else:
            return {"code": close_order['code'], "ordId": None, "instId": instrument_id, "posSide": None}
    else:
        return {"code": close_order['code'], "ordId": None, "instId": instrument_id, "posSide": None}

async def wait_for_close_order(accountAPI, instId, posSide):
    if posSide is None:  # 如果 posSide 为 None，则不需要等待
        return

    while True:
        positions = accountAPI.get_positions(instId=instId)
        position_exists = False

        for position in positions['data']:
            if position['posSide'] == posSide:
                position_exists = True
                break

        if not position_exists:
            break
        else:
            await asyncio.sleep(1)

def get_message_code(data, code):
    for msg in data['message']:
        if code in msg:
            return msg[code]
    return None

async def close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position):
    close_order_id = None
    if long_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed long position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])
            close_order_id = close_order['ordId']  # return the order id if a position was closed
    if short_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed short position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])
            close_order_id = close_order['ordId']  # return the order id if a position was closed
    return close_order_id if close_order_id is not None else None