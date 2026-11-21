# EVM公链查询助手

Python 3.10+，仅使用标准库。支持兼容以太坊 JSON-RPC 的 EVM 公链。工具只调用读取接口，不需要私钥，也不发送交易。

## 使用方法

1. 编辑与 `main.py` 同级的 `config.json`。先设置 `network.chain_id` 和 `network.rpc_urls`，再设置 `query` 中的范围与过滤条件。
2. 在本目录运行 `python main.py` 打开图形界面，点击“开始查询”；无界面环境运行 `python main.py --cli`。界面右上角可随时切换中文与英语，已显示的表格列名、状态、数据来源和详情也会立即切换，无须重新查询。语言选择保存在 `config.json` 的 `ui.language`（`zh` 或 `en`）。
3. 查询结束后自动把 JSON（含原始交易与回执）及表格 CSV 写入同级 `result` 目录。达到 `max_blocks` 或 `max_results` 上限时会停止、显示已取得的记录，并将 JSON 中的 `complete` 设为 `false`、`stop_reason` 设为对应参数名。取消时也会标记为不完整。

英文使用说明见 [README_EN.md](README_EN.md)。CSV、JSON 使用稳定的英文字段名和状态值，切换界面语言不会修改已导出的文件。

默认配置以 Anubis 链上的 LGNS BurnBond 为例：按一小时范围扫描发往 BurnBond 的直接交易，同时扫描 Vault 中指定事件；两种来源的交易按哈希合并。**通用记录只显示原生币转账金额、执行状态与手续费；LGNS 代币到账量需要另加该业务的解析规则。** 示例中的日期仅供演示，运行前请改为所需时间。

## config.json 参数

| 参数 | 说明 |
|---|---|
| `ui.language` | 界面与命令行提示语言：`zh` 或 `en` |
| `network.name` | 网络名称，用于显示和文件名 |
| `network.chain_id` | 期望的 EVM Chain ID；查询前与节点核对 |
| `network.rpc_urls` | 主备 HTTP(S) JSON-RPC 地址数组 |
| `network.native_symbol` | 原生币符号，仅作说明 |
| `query.start_time` / `end_time` | ISO 8601 时间，必须带时区；起点包含、终点不包含 |
| `query.start_block` / `end_block` | 可选的区块范围，两个都填写时优先于时间；两端都包含 |
| `query.scan_transactions` | 是否逐块读取并筛选交易 |
| `query.from_addresses` / `to_addresses` | 发起地址、接收地址白名单；同组任一匹配，非空组之间同时满足 |
| `query.any_addresses` | 发起或接收地址任一匹配 |
| `query.method_selectors` | 四字节方法选择器白名单，例如 `0x379607f5`；空数组表示不限 |
| `query.log_filters` | `eth_getLogs` 过滤器数组；每项支持 `address` 和 `topics`；日志命中的交易独立加入结果 |
| `options.request_timeout` | 单次 RPC 超时，秒 |
| `options.block_batch` / `log_batch` | 区块头批量请求数、日志请求的区块跨度 |
| `options.full_block_batch` / `rpc_retries` | 单次读取完整区块的最大批量数、主备节点失败后的重试轮数；默认分别为 `5` 和 `2` |
| `options.receipt_batch` | 每批核对的交易回执数；默认 `50` |
| `options.concurrency` | 批量 RPC 不可用时，并发逐条读取的最大请求数；默认 `6` |
| `options.max_blocks` / `max_results` | 最大扫描区块数、最大结果数；触及上限即停止并导出部分结果 |
| `options.confirmations` | 距链头保留的确认区块数 |

日志过滤规则采用 EVM RPC 语义：`topics` 的位置有意义，`null` 表示该位置不限。`log_filters` 各项取并集；交易扫描条件命中的交易与日志命中的交易也取并集。需要全区块交易时，把地址和方法条件设为空数组；大型范围的全区块扫描请求量较高，应适当缩小范围。

## 覆盖与限制

扫描范围受节点提供的历史数据、RPC 限流和 `max_blocks` 限制。程序不会解析任意合约 ABI、内部调用或代币净到账，也不会凭成功日志推断失败的间接调用。结果中的 `matched_log_count` 是命中配置过滤器的日志条数。若 RPC 读取失败，查询会报错，不会把缺失的数据伪装成完整结果。

模块分工：`config.py` 校验配置，`rpc.py` 连接节点，`discovery.py` 扫描区块与日志，`parsing.py` 生成通用记录，`query.py` 编排流程，`export.py` 导出，`main.py` 提供界面与命令行入口。
