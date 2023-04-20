
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
