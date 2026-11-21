"""Read-only EVM JSON-RPC client with endpoint failover."""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

class RpcClient:
    def __init__(self, urls, timeout=20, retries=2, concurrency=6):
        self.urls, self.timeout, self.retries = urls, timeout, retries
        self.concurrency = max(1, min(16, concurrency))
        self.batch_supported = True

    def _request(self, url, payload):
        request = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    @staticmethod
    def _value(data):
        if not isinstance(data, dict): raise ValueError("RPC 响应不是对象")
        if "error" in data: raise RuntimeError(str(data["error"]))
        if "result" not in data: raise ValueError("RPC 响应缺少 result")
        return data["result"]

    def call(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        errors = []
        for attempt in range(self.retries):
            for url in self.urls:
                try: return self._value(self._request(url, payload))
                except Exception as exc: errors.append(f"{url} (attempt {attempt + 1}): {exc}")
            if attempt + 1 < self.retries:
                time.sleep(min(2, attempt + 1))
        raise RuntimeError(f"{method} 请求失败：" + "; ".join(errors))

    def batch(self, calls):
        if not calls: return []
        if len(calls) == 1:
            return [self.call(*calls[0])]
        if not self.batch_supported:
            return self._parallel_calls(calls)
        payload = [{"jsonrpc": "2.0", "id": i, "method": method, "params": params}
                   for i, (method, params) in enumerate(calls)]
        for url in self.urls:
            try:
                data = self._request(url, payload)
                if not isinstance(data, list): raise ValueError("节点未返回批量响应")
                by_id = {item["id"]: item for item in data}
                if len(by_id) != len(calls): raise ValueError("批量响应缺少条目")
                return [self._value(by_id[i]) for i in range(len(calls))]
            except Exception: continue
        self.batch_supported = False
        return self._parallel_calls(calls)

    def _parallel_calls(self, calls):
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            return list(pool.map(lambda call: self.call(*call), calls))
