"""Translations for the GUI and its normalized result table."""

TEXT = {
    "zh": {
        "title": "EVM公链查询助手", "start": "开始查询", "cancel": "取消",
        "switch": "English", "config": "配置", "result_dir": "结果目录",
        "ready": "点击查询后读取 config.json", "config_error": "配置错误",
        "querying": "正在查询 {network}…", "cancelling": "正在取消；已完成记录将标记为不完整",
        "progress": "{stage}：{done}/{total}", "query_failed": "查询失败",
        "done": "完成", "cancelled": "已取消，结果不完整",
        "max_blocks": "达到 max_blocks 上限，结果不完整",
        "max_results": "达到 max_results 上限，结果不完整",
        "done_status": "{state}；{count} 笔；JSON：{json_path}；CSV：{csv_path}",
        "summary": "{network} · Chain ID {chain_id} · 区块 {start}–{end}",
        "summary_partial": "{network} · Chain ID {chain_id} · 已扫描至区块 {last}，请求终点 {requested}",
        "detail": "交易详情", "raw": "原始证据", "none": "—",
        "success": "成功", "reverted": "回滚", "unknown": "未确认",
        "transaction": "交易扫描", "log": "事件日志", "transaction+log": "交易与事件日志",
        "区块扫描": "区块扫描", "日志扫描": "日志扫描", "回执核对": "回执核对",
    },
    "en": {
        "title": "EVM Chain Query Assistant", "start": "Start query", "cancel": "Cancel",
        "switch": "中文", "config": "Config", "result_dir": "Results",
        "ready": "Click Start query to load config.json", "config_error": "Configuration error",
        "querying": "Querying {network}…", "cancelling": "Cancelling; completed records will be marked incomplete",
        "progress": "{stage}: {done}/{total}", "query_failed": "Query failed",
        "done": "Complete", "cancelled": "Cancelled; results incomplete",
        "max_blocks": "Stopped at max_blocks; results incomplete",
        "max_results": "Stopped at max_results; results incomplete",
        "done_status": "{state}; {count} transactions; JSON: {json_path}; CSV: {csv_path}",
        "summary": "{network} · Chain ID {chain_id} · Blocks {start}–{end}",
        "summary_partial": "{network} · Chain ID {chain_id} · Scanned through block {last}; requested end {requested}",
        "detail": "Transaction details", "raw": "Raw evidence", "none": "—",
        "success": "Success", "reverted": "Reverted", "unknown": "Unconfirmed",
        "transaction": "Block scan", "log": "Event logs", "transaction+log": "Block scan and event logs",
        "区块扫描": "Scanning blocks", "日志扫描": "Scanning logs", "回执核对": "Checking receipts",
    },
}

COLUMNS = {
    "zh": ("UTC时间", "区块", "块内位置", "交易哈希", "发起地址", "接收地址",
           "方法选择器", "原生币数量", "状态", "Gas用量", "Gas价格（Wei）",
           "手续费（原生币）", "匹配日志数", "数据来源"),
    "en": ("UTC Time", "Block", "Tx Index", "Transaction Hash", "From", "To",
           "Method Selector", "Native Value", "Status", "Gas Used", "Gas Price (Wei)",
           "Fee (Native)", "Matched Logs", "Source"),
}


def tr(language, key, **values):
    return TEXT[language].get(key, key).format(**values)


def result_state(language, result):
    return tr(language, "done" if result["complete"] else result.get("stop_reason") or "cancelled")


def display_value(language, field, value):
    if field in ("status", "source"):
        return tr(language, value if value is not None else "unknown")
    return tr(language, "none") if value is None else value
