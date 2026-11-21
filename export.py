"""Write query artifacts under the project's result directory."""
import csv
import json
import re
from datetime import datetime, timezone

from config import RESULT_DIR

FIELDS = ("time_utc", "block", "transaction_index", "hash", "from", "to",
          "method_selector", "value_native", "status", "gas_used", "gas_price_wei",
          "fee_native", "matched_log_count", "source")

def save_result(result):
    RESULT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    safe_network = re.sub(r'[^\w.-]', '_', result['network'])
    stem = f"{safe_network}_{result['chain_id']}_{stamp}"
    json_path = RESULT_DIR / f"{stem}.json"
    csv_path = RESULT_DIR / f"{stem}.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow({key: row.get(key) for key in FIELDS})
    return json_path, csv_path
