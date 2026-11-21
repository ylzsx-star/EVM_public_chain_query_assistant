# EVM Chain Query Assistant

This read-only tool queries EVM chains through Ethereum-compatible JSON-RPC endpoints. It requires Python 3.10 or later and uses only the standard library. No private key is needed; the tool does not submit transactions.

## Quick start

1. Open `config.json` in the same directory as `main.py`. Set `network.chain_id` and `network.rpc_urls`, then choose a query range and filters under `query`.
2. Run `python main.py` from this directory and click **Start query**. For a terminal-only run, use `python main.py --cli`.
3. The tool writes a CSV table and a JSON file containing the full records and raw evidence to the sibling `result` directory.

Use the button in the upper-right corner to switch between English and Chinese. Column headings, status and source values, progress, and the selected transaction's details update immediately, including results already on screen. The selected language is saved as `ui.language` in `config.json`: use `en` for English or `zh` for Chinese. The CLI also uses this setting for progress messages. Exported CSV and JSON retain stable English field names and machine-readable values regardless of the UI language.

The bundled configuration is an **LGNS example on Anubis**. It scans transactions sent to BurnBond and matching Vault event logs during a one-hour window. Change the example dates before running it. Generic records include native-token value, transaction status, gas, and fee; they do not calculate LGNS token proceeds.

## Configuration reference

| Setting | Meaning |
|---|---|
| `ui.language` | `en` or `zh` |
| `network.name` | Display name and output-file prefix |
| `network.chain_id` | Expected EVM chain ID; checked against the RPC endpoint |
| `network.rpc_urls` | Ordered list of HTTP(S) JSON-RPC endpoints for failover |
| `network.native_symbol` | Informational native-token symbol |
| `query.start_time`, `end_time` | ISO 8601 timestamps with a timezone; start inclusive, end exclusive |
| `query.start_block`, `end_block` | Optional block range; both endpoints inclusive. If both are set, they override the time range |
| `query.scan_transactions` | Read full blocks and filter their transactions |
| `query.from_addresses`, `to_addresses` | Sender and recipient allowlists; values within a list are alternatives, nonempty lists are combined |
| `query.any_addresses` | Match an address in either sender or recipient |
| `query.method_selectors` | Four-byte method selectors such as `0x379607f5`; an empty list applies no method filter |
| `query.log_filters` | Array of `eth_getLogs` filters, each with `address` and/or `topics` |
| `options.request_timeout` | Timeout per RPC request, in seconds |
| `options.block_batch`, `log_batch` | Batch size for block headers and block span for log queries |
| `options.full_block_batch`, `rpc_retries` | Maximum full blocks per batch and number of endpoint retry rounds; defaults are `5` and `2` |
| `options.receipt_batch` | Transaction receipts checked per batch; defaults to `50` |
| `options.concurrency` | Maximum concurrent individual requests when batch RPC is unavailable; defaults to `6` |
| `options.max_blocks`, `max_results` | Limits on scanned blocks and matching transactions; reaching either stops the query and exports partial results |
| `options.confirmations` | Number of blocks to stay behind the current head |

`topics` follow Ethereum JSON-RPC rules: positions matter, and `null` leaves a position unrestricted. Matches from separate log filters are combined. Transactions matching the block-scan filters and transactions containing matching logs are also combined by transaction hash. To scan all transactions in a range, leave the address and method lists empty. Keep that range small if your RPC provider has request limits.

## Output and limits

Each completed query produces `result/<network>_<chain-id>_<timestamp>.json` and `.csv`. The JSON includes query metadata, a `complete` flag, normalized rows, and raw transactions, receipts, and matching logs. If `max_blocks` or `max_results` is reached, the query stops and exports the records collected so far with `complete: false` and a matching `stop_reason`. The JSON also records the requested end block and the last scanned block. Cancellation likewise marks results incomplete. A failed RPC read raises an error rather than silently presenting missing data as complete.

Historical coverage depends on the RPC provider, rate limits, and `options.max_blocks`. The generic parser does not decode arbitrary contract ABIs, internal calls, or token proceeds. A successful event log cannot reveal failed indirect calls.

Modules: `config.py` validates settings; `rpc.py` talks to nodes; `discovery.py` scans blocks and logs; `parsing.py` normalizes records; `query.py` coordinates the query; `export.py` writes files; `main.py` provides the GUI and CLI.
