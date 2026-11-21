"""Coordinate generic EVM block, transaction and event queries."""
from datetime import datetime

from discovery import block_at_or_after, blocks_in_range, logs_in_range
from parsing import make_record, matches_transaction
from rpc import RpcClient


def run_query(cfg, cancelled=None, progress=None):
    from threading import Event
    cancelled = cancelled or Event()
    progress = progress or (lambda stage, done, total: None)
    network, query, options = cfg["network"], cfg["query"], cfg["options"]
    rpc = RpcClient(network["rpc_urls"], int(options["request_timeout"]),
                    int(options.get("rpc_retries", 2)), int(options.get("concurrency", 6)))
    chain_id = int(rpc.call("eth_chainId"), 16)
    if chain_id != int(network["chain_id"]):
        raise RuntimeError(f"Chain ID 不符：配置 {network['chain_id']}，RPC {chain_id}")
    head = int(rpc.call("eth_blockNumber"), 16)
    safe_head = head - int(options.get("confirmations", 0))
    if safe_head < 0: raise RuntimeError("确认数大于当前区块高度")
    if query.get("start_block") is not None:
        start, end = int(query["start_block"]), min(int(query["end_block"]), safe_head)
    else:
        start_ts = int(datetime.fromisoformat(query["start_time"]).timestamp())
        end_ts = int(datetime.fromisoformat(query["end_time"]).timestamp())
        start = block_at_or_after(rpc, start_ts, safe_head)
        end = min(block_at_or_after(rpc, end_ts, safe_head) - 1, safe_head)
    requested_end = end
    block_limited = end >= start and end - start + 1 > int(options["max_blocks"])
    if block_limited:
        end = start + int(options["max_blocks"]) - 1
    candidates, blocks = {}, {}
    max_results = int(options["max_results"])
    stop_reason = None
    last_scanned_block = start - 1
    if end >= start and query["log_filters"]:
        logs, result_limited, last_scanned_block = logs_in_range(
            rpc, start, end, query["log_filters"], int(options["log_batch"]),
            cancelled, lambda done, total: progress("日志扫描", done, total), max_results)
        for txhash, items in logs.items():
            candidates[txhash] = {"logs": items, "source": "log"}
        if result_limited:
            stop_reason = "max_results"
    if end >= start and query.get("scan_transactions", True) and not cancelled.is_set() and stop_reason is None:
        for block in blocks_in_range(rpc, start, end, int(options["block_batch"]),
                                     int(options.get("full_block_batch", 5)), cancelled,
                                     lambda done, total: progress("区块扫描", done, total)):
            number = int(block["number"], 16)
            last_scanned_block = number
            for tx in block["transactions"]:
                if matches_transaction(tx, query):
                    blocks[number] = block
                    item = candidates.setdefault(tx["hash"].lower(), {"logs": [], "source": "transaction"})
                    if item["source"] == "log": item["source"] = "transaction+log"
                    item["tx"] = tx
                    if len(candidates) >= max_results:
                        stop_reason = "max_results"
                        break
            if stop_reason is not None:
                break
    rows = []
    hashes = list(candidates)
    receipt_batch = int(options.get("receipt_batch", 50))
    for offset in range(0, len(hashes), receipt_batch):
        if cancelled.is_set(): break
        batch = hashes[offset:offset + receipt_batch]
        missing = [h for h in batch if "tx" not in candidates[h]]
        if missing:
            transactions = rpc.batch([("eth_getTransactionByHash", [h]) for h in missing])
            for h, tx in zip(missing, transactions):
                if tx is None: raise RuntimeError(f"交易不存在：{h}")
                candidates[h]["tx"] = tx
        receipts = rpc.batch([("eth_getTransactionReceipt", [h]) for h in batch])
        for h, receipt in zip(batch, receipts):
            item = candidates[h]
            tx = item["tx"]
            if tx.get("blockNumber") is None: raise RuntimeError(f"交易尚未上链：{h}")
            number = int(tx["blockNumber"], 16)
            if number not in blocks:
                blocks[number] = rpc.call("eth_getBlockByNumber", [hex(number), False])
            if blocks[number] is None: raise RuntimeError(f"区块不存在：{number}")
            rows.append(make_record(tx, receipt, blocks[number], item["logs"], item["source"]))
        progress("回执核对", min(offset + len(batch), len(hashes)), len(hashes))
    rows.sort(key=lambda row: (row["block"], row["transaction_index"], row["hash"]))
    return {
        "project": "EVM公链查询助手", "network": network["name"], "chain_id": chain_id,
        "start_block": start, "end_block": end, "requested_end_block": requested_end,
        "last_scanned_block": last_scanned_block, "head_block": head,
        "complete": not cancelled.is_set() and stop_reason is None and not block_limited,
        "stop_reason": "cancelled" if cancelled.is_set() else stop_reason or ("max_blocks" if block_limited else None),
        "query": query, "rows": rows
    }
