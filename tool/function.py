
# tool/function.py

import asyncio

async def close_position(instrument_id, tradeAPI):
    print(f"Closing position for {instrument_id}...")
    close_order = tradeAPI.close_positions(instId=instrument_id, ccy='USDT', mgnMode="isolated")
    await asyncio.sleep(1)  # add delay here
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

async def close_positions_if_exists(instrument_id, tradeAPI, accountAPI, long_position, short_position, trade_info, instrument_ids, trade_info_lock):
    close_order_id = None
    closed = False  # 用于确认是否成功平仓

    if long_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed long position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])
            closed = True  # 更新状态为已成功平仓

    if short_position:
        close_order = await close_position(instrument_id, tradeAPI)
        print(f"Closed short position: {close_order}")
        if close_order['code'] == '0':
            await wait_for_close_order(accountAPI, close_order['instId'], close_order['posSide'])
            closed = True  # 更新状态为已成功平仓


    async with trade_info_lock:  # 使用锁来保护共享资源
        if closed:
            print("Attempting to update trade_info for closed position.")  # New log line
            keys_to_delete = [symbol for symbol, info in trade_info.items() if info.get('instrument_id') == instrument_id]
            for key in keys_to_delete:
                del trade_info[key]
            print(f"Updated trade_info: {trade_info}")  # New log line

    return "Closed" if closed else "Failed to close any position"

def format_position_info(position):
    pos = float(position['pos'])
    if pos > 0:
        return f"Long position for {position['instId']}: {pos}"
    elif pos < 0:
        return f"Short position for {position['instId']}: {-pos}"  # 使用负数使输出为正数
    else:
        return f"No position for {position['instId']}"

# 在程序启动时初始化 trade_info
async def initialize_trade_info(instrument_ids,accountAPI,trade_info):
    for instrument_id in instrument_ids.values():
        positions = accountAPI.get_positions(instId=instrument_id)
        long_position = None
        short_position = None

        for position in positions['data']:
            print(format_position_info(position))  # 打印持仓信息

            pos = float(position['pos'])
            if pos > 0:
                long_position = position
            elif pos < 0:
                short_position = position
            
            await asyncio.sleep(0.2)  # Add a delay after each position

        if long_position is not None:
            trade_info[instrument_id] = {
                "order_id": long_position['posId'],
                "direction": "Long Entry"
            }
        elif short_position is not None:
            trade_info[instrument_id] = {
                "order_id": short_position['posId'],
                "direction": "Short Entry"
            }

async def place_new_order(instrument_id, side, accountAPI, tradeAPI, trade_info, instrument_ids, symbol, direction,trade_info_lock):
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
            async with trade_info_lock: # 使用鎖來保護共享資源
                # Update trade_info after a successful order
                trade_info[symbol] = {"order_id": order['data'][0]['ordId'], "direction": direction}
                print(f"Order placed successfully for {symbol}. Order ID: {order['data'][0]['ordId']}")
                break
        elif i == 3:  # If it's the last attempt
            raise Exception('Failed to place order after 3 attempts')
        await asyncio.sleep(1)  # Add a delay after each attempt