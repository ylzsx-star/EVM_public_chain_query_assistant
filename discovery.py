"""Discover transactions by blocks and EVM event logs."""

def block_at_or_after(rpc, timestamp, head):
    low, high = 0, head + 1
    while low < high:
        middle = (low + high) // 2
        block = rpc.call("eth_getBlockByNumber", [hex(middle), False])
        if block is None: raise RuntimeError(f"无法读取区块 {middle}")
        if int(block["timestamp"], 16) < timestamp: low = middle + 1
        else: high = middle
    return low

def blocks_in_range(rpc, start, end, batch_size, full_batch_size, cancelled, progress):
    for first in range(start, end + 1, batch_size):
        if cancelled.is_set(): return
        last = min(end, first + batch_size - 1)
        headers = rpc.batch([("eth_getBlockByNumber", [hex(n), False]) for n in range(first, last + 1)])
        if any(block is None for block in headers): raise RuntimeError(f"区块 {first}–{last} 有缺失")
        blocks = {}
        populated = [block for block in headers if block["transactions"]]
        for offset in range(0, len(populated), full_batch_size):
            if cancelled.is_set(): return
            part = populated[offset:offset + full_batch_size]
            full = rpc.batch([("eth_getBlockByNumber", [block["number"], True]) for block in part])
            for block in full:
                if block is None: raise RuntimeError("完整区块读取失败")
                blocks[int(block["number"], 16)] = block
        progress(last - start + 1, end - start + 1)
        for header in headers:
            yield blocks.get(int(header["number"], 16), header)

def logs_in_range(rpc, start, end, log_filters, batch_size, cancelled, progress, max_results=None):
    def fetch(first, last, item):
        if cancelled.is_set(): return []
        filt = {"fromBlock": hex(first), "toBlock": hex(last), **item}
        try: return rpc.call("eth_getLogs", [filt])
        except Exception:
            if first == last: raise
            middle = (first + last) // 2
            return fetch(first, middle, item) + fetch(middle + 1, last, item)
    found = {}
    total, done = (end - start + 1) * len(log_filters), 0
    last_block = start - 1
    for item in log_filters:
        for first in range(start, end + 1, batch_size):
            if cancelled.is_set(): return found, False, last_block
            last = min(end, first + batch_size - 1)
            for log in fetch(first, last, item):
                if not log.get("removed", False):
                    found.setdefault(log["transactionHash"].lower(), []).append(log)
                    if max_results is not None and len(found) >= max_results:
                        return found, True, int(log["blockNumber"], 16)
            done += last - first + 1
            last_block = last
            progress(done, total)
    return found, False, last_block
