"""Normalize EVM transactions and receipts without chain-specific rules."""
from datetime import datetime, timezone
from decimal import Decimal

def hex_int(value):
    return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value or 0)

def matches_transaction(tx, query):
    sender = (tx.get("from") or "").lower()
    target = (tx.get("to") or "").lower()
    if query["from_addresses"] and sender not in {a.lower() for a in query["from_addresses"]}: return False
    if query["to_addresses"] and target not in {a.lower() for a in query["to_addresses"]}: return False
    if query["any_addresses"] and not ({sender, target} & {a.lower() for a in query["any_addresses"]}): return False
    selectors = query["method_selectors"]
    if selectors and (tx.get("input") or "")[:10].lower() not in {s.lower() for s in selectors}: return False
    return True

def make_record(tx, receipt, block, matched_logs, source):
    gas = hex_int(receipt["gasUsed"]) if receipt else None
    price = hex_int(receipt.get("effectiveGasPrice") or tx.get("gasPrice")) if receipt else None
    fee = str(Decimal(gas * price) / Decimal(10**18)) if gas is not None and price is not None else None
    timestamp = hex_int(block["timestamp"])
    return {
        "time_utc": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
        "block": hex_int(tx["blockNumber"]),
        "transaction_index": hex_int(tx.get("transactionIndex")),
        "hash": tx["hash"], "from": tx.get("from"), "to": tx.get("to"),
        "method_selector": (tx.get("input") or "")[:10].lower(),
        "value_native": str(Decimal(hex_int(tx.get("value"))) / Decimal(10**18)),
        "status": None if receipt is None else ("success" if hex_int(receipt["status"]) == 1 else "reverted"),
        "gas_used": gas, "gas_price_wei": price, "fee_native": fee,
        "matched_log_count": len(matched_logs), "source": source,
        "raw": {"transaction": tx, "receipt": receipt, "matched_logs": matched_logs}
    }
