"""Load and validate the local query configuration."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
RESULT_DIR = ROOT / "result"

def load_config():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    network, query, options = cfg["network"], cfg["query"], cfg["options"]
    if not network.get("rpc_urls") or not all(str(url).startswith(("http://", "https://")) for url in network["rpc_urls"]):
        raise ValueError("network.rpc_urls 必须包含 HTTP(S) RPC 地址")
    if int(network["chain_id"]) < 0: raise ValueError("chain_id 无效")
    for key in ("from_addresses", "to_addresses", "any_addresses"):
        query.setdefault(key, [])
        for address in query[key]:
            if not isinstance(address, str) or len(address) != 42 or not address.startswith("0x"):
                raise ValueError(f"{key} 包含无效 EVM 地址：{address}")
    query.setdefault("method_selectors", [])
    for selector in query["method_selectors"]:
        if not isinstance(selector, str) or len(selector) != 10 or not selector.startswith("0x"):
            raise ValueError(f"无效方法选择器：{selector}")
    query.setdefault("log_filters", [])
    if not query.get("scan_transactions", True) and not query["log_filters"]:
        raise ValueError("必须启用区块交易扫描或配置至少一个日志过滤器")
    for item in query["log_filters"]:
        if not item.get("address") and not item.get("topics"):
            raise ValueError("日志过滤器至少需要 address 或 topics")
        if set(item) - {"address", "topics"}:
            raise ValueError("日志过滤器只支持 address 和 topics")
    blocks = query.get("start_block") is not None or query.get("end_block") is not None
    if blocks:
        if query.get("start_block") is None or query.get("end_block") is None:
            raise ValueError("start_block 和 end_block 必须同时填写")
        if int(query["start_block"]) < 0 or int(query["end_block"]) < int(query["start_block"]):
            raise ValueError("区块范围无效")
    else:
        start = datetime.fromisoformat(query["start_time"])
        end = datetime.fromisoformat(query["end_time"])
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("时间必须包含时区，且 end_time 晚于 start_time")
    for key in ("request_timeout", "block_batch", "log_batch", "max_blocks", "max_results"):
        if int(options[key]) <= 0: raise ValueError(f"options.{key} 必须大于 0")
    for key in ("full_block_batch", "receipt_batch", "rpc_retries", "concurrency"):
        if int(options.get(key, 2)) <= 0: raise ValueError(f"options.{key} 必须大于 0")
    if int(options.get("confirmations", 0)) < 0: raise ValueError("confirmations 不能为负数")
    return cfg
