"""GUI and CLI entry points for the EVM Chain Query Assistant."""
import argparse
import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from config import CONFIG_PATH, RESULT_DIR, load_config
from export import FIELDS, save_result
from i18n import COLUMNS, display_value, result_state, tr
from query import run_query


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1380x760")
        self.events = queue.Queue()
        self.cancelled = threading.Event()
        self.rows = {}
        self.language = self._stored_language()
        self.view_state = ("ready",)
        self.last_result = None
        self.status = tk.StringVar()
        self.summary = tk.StringVar()

        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        self.start_button = ttk.Button(bar, command=self.start_query)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(bar, command=self.cancel_query, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.language_button = ttk.Button(bar, command=self.toggle_language)
        self.language_button.pack(side="right")
        self.result_label = ttk.Label(bar)
        self.result_label.pack(side="right", padx=16)
        ttk.Label(self, textvariable=self.status, padding=8).pack(fill="x")
        ttk.Label(self, textvariable=self.summary, padding=8).pack(fill="x")

        self.table = ttk.Treeview(self, columns=FIELDS, show="headings", selectmode="browse")
        for field in FIELDS:
            self.table.column(field, width=130, stretch=False)
        for field in ("hash", "from", "to"):
            self.table.column(field, width=310)
        self.table.column("time_utc", width=210)
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.table.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.table.pack(fill="both", expand=True, padx=10)
        yscroll.place(relx=.985, rely=.15, relheight=.58)
        xscroll.pack(fill="x", padx=10)
        self.detail = tk.Text(self, height=12, wrap="none")
        self.detail.pack(fill="x", padx=10, pady=10)
        self.table.bind("<<TreeviewSelect>>", self.show_detail)
        self.refresh_language()
        self.after(100, self.poll_events)

    @staticmethod
    def _stored_language():
        try:
            value = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("ui", {}).get("language")
            return value if value in ("zh", "en") else "zh"
        except (OSError, ValueError, TypeError):
            return "zh"

    def toggle_language(self):
        target = "en" if self.language == "zh" else "zh"
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.setdefault("ui", {})["language"] = target
            CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(tr(self.language, "config_error"), str(exc))
            return
        self.language = target
        self.refresh_language()

    def refresh_language(self):
        self.title(tr(self.language, "title"))
        self.start_button.configure(text=tr(self.language, "start"))
        self.cancel_button.configure(text=tr(self.language, "cancel"))
        self.language_button.configure(text=tr(self.language, "switch"))
        self.result_label.configure(text=f"{tr(self.language, 'result_dir')}: {RESULT_DIR}")
        for field, label in zip(FIELDS, COLUMNS[self.language]):
            self.table.heading(field, text=label)
        for txhash, row in self.rows.items():
            self.table.item(txhash, values=[display_value(self.language, field, row.get(field)) for field in FIELDS])
        self._render_status()
        self.show_detail()

    def _render_status(self):
        kind, *data = self.view_state
        if kind == "ready":
            self.status.set(f"{tr(self.language, 'config')}: {CONFIG_PATH}")
        elif kind == "querying":
            self.status.set(tr(self.language, "querying", network=data[0]))
        elif kind == "cancelling":
            self.status.set(tr(self.language, "cancelling"))
        elif kind == "progress":
            stage, done, total = data
            self.status.set(tr(self.language, "progress", stage=tr(self.language, stage), done=done, total=total))
        elif kind == "error":
            self.status.set(f"{tr(self.language, 'query_failed')}: {data[0]}")
        elif kind == "done":
            result, paths = data
            state = result_state(self.language, result)
            self.status.set(tr(self.language, "done_status", state=state, count=len(result["rows"]),
                               json_path=paths[0], csv_path=paths[1]))
        if self.last_result is None:
            self.summary.set(tr(self.language, "ready"))
        elif self.last_result["complete"]:
            self.summary.set(tr(self.language, "summary", network=self.last_result["network"],
                                chain_id=self.last_result["chain_id"], start=self.last_result["start_block"],
                                end=self.last_result["end_block"]))
        else:
            self.summary.set(tr(self.language, "summary_partial", network=self.last_result["network"],
                                chain_id=self.last_result["chain_id"],
                                last=self.last_result["last_scanned_block"],
                                requested=self.last_result["requested_end_block"]))

    def start_query(self):
        try:
            cfg = load_config()
        except Exception as exc:
            messagebox.showerror(tr(self.language, "config_error"), str(exc))
            return
        self.cancelled.clear()
        self.rows.clear()
        self.last_result = None
        self.table.delete(*self.table.get_children())
        self.detail.delete("1.0", "end")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.view_state = ("querying", cfg["network"]["name"])
        self._render_status()
        threading.Thread(target=self.worker, args=(cfg,), daemon=True).start()

    def cancel_query(self):
        self.cancelled.set()
        self.view_state = ("cancelling",)
        self._render_status()

    def worker(self, cfg):
        try:
            result = run_query(cfg, self.cancelled,
                               lambda stage, done, total: self.events.put(("progress", stage, done, total)))
            paths = save_result(result)
            self.events.put(("done", result, paths))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self):
        try:
            while True:
                kind, *data = self.events.get_nowait()
                if kind == "progress":
                    if not self.cancelled.is_set():
                        self.view_state = (kind, *data)
                        self._render_status()
                elif kind == "error":
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.view_state = (kind, *data)
                    self._render_status()
                    messagebox.showerror(tr(self.language, "query_failed"), data[0])
                elif kind == "done":
                    result, paths = data
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.last_result = result
                    self.rows = {row["hash"].lower(): row for row in result["rows"]}
                    for txhash, row in self.rows.items():
                        self.table.insert("", "end", iid=txhash,
                                          values=[display_value(self.language, field, row.get(field)) for field in FIELDS])
                    self.view_state = (kind, result, paths)
                    self._render_status()
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def show_detail(self, _event=None):
        selected = self.table.selection()
        self.detail.delete("1.0", "end")
        if not selected:
            return
        row = self.rows[selected[0]]
        fields = [f"{label}: {display_value(self.language, field, row.get(field))}"
                  for field, label in zip(FIELDS, COLUMNS[self.language])]
        evidence = json.dumps(row["raw"], ensure_ascii=False, indent=2)
        self.detail.insert("1.0", "\n".join(fields) + f"\n\n{tr(self.language, 'raw')}:\n" + evidence)


def main():
    parser = argparse.ArgumentParser(description="EVM Chain Query Assistant / EVM公链查询助手")
    parser.add_argument("--cli", action="store_true", help="Run without a GUI and export to result")
    args = parser.parse_args()
    if args.cli:
        cfg = load_config()
        language = cfg.get("ui", {}).get("language", "zh")
        if language not in ("zh", "en"):
            language = "zh"
        result = run_query(cfg, progress=lambda stage, done, total:
                           print("\r" + tr(language, "progress", stage=tr(language, stage),
                                           done=done, total=total), end="", flush=True))
        paths = save_result(result)
        print("\n" + tr(language, "done_status", state=result_state(language, result),
                        count=len(result["rows"]), json_path=paths[0], csv_path=paths[1]))
    else:
        App().mainloop()


if __name__ == "__main__":
    main()
