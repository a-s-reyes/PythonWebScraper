import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from crawler import AVAILABLE_PIPELINES, CrawlConfig, Crawler


class CrawlerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Web Crawler")
        self.geometry("1000x600")
        self.minsize(700, 400)

        self.seed_var = tk.StringVar()
        self.depth_var = tk.IntVar(value=3)
        self.max_pages_var = tk.IntVar(value=100)
        self.workers_var = tk.IntVar(value=4)
        self.rate_var = tk.DoubleVar(value=0.5)
        self.same_domain_var = tk.BooleanVar(value=True)
        self.robots_var = tk.BooleanVar(value=True)
        self.pipeline_var = tk.StringVar(value=AVAILABLE_PIPELINES[0].name)
        self.status_var = tk.StringVar(value="Idle")

        self._crawler = None
        self._crawler_thread = None
        self._event_queue = queue.Queue()
        self._row_urls = []
        self._counts = {"crawled": 0, "enqueued": 0, "skipped": 0, "errors": 0}

        self._build_ui()

    def _build_ui(self):
        row1 = ttk.Frame(self, padding=8)
        row1.pack(fill="x")
        ttk.Label(row1, text="Seed URL:").pack(side="left")
        entry = ttk.Entry(row1, textvariable=self.seed_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<Return>", lambda e: self._start())
        entry.focus_set()
        self.start_btn = ttk.Button(row1, text="Start", command=self._start)
        self.start_btn.pack(side="left", padx=2)
        self.stop_btn = ttk.Button(row1, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=2)

        row2 = ttk.Frame(self, padding=(8, 0))
        row2.pack(fill="x")
        self._int_field(row2, "Depth:", self.depth_var, 5)
        self._int_field(row2, "Max pages:", self.max_pages_var, 6)
        self._int_field(row2, "Workers:", self.workers_var, 4)
        self._float_field(row2, "Rate (s):", self.rate_var, 5)
        ttk.Checkbutton(row2, text="Same domain", variable=self.same_domain_var).pack(side="left", padx=6)
        ttk.Checkbutton(row2, text="Respect robots.txt", variable=self.robots_var).pack(side="left", padx=6)

        row3 = ttk.Frame(self, padding=(8, 4))
        row3.pack(fill="x")
        ttk.Label(row3, text="Pipeline:").pack(side="left")
        pipe_names = [p.name for p in AVAILABLE_PIPELINES]
        ttk.Combobox(
            row3, textvariable=self.pipeline_var, values=pipe_names,
            state="readonly", width=25,
        ).pack(side="left", padx=6)

        table = ttk.Frame(self, padding=8)
        table.pack(fill="both", expand=True)
        cols = ("depth", "status", "url")
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        self.tree.heading("depth", text="Depth")
        self.tree.heading("status", text="Status")
        self.tree.heading("url", text="URL")
        self.tree.column("depth", width=60, anchor="center", stretch=False)
        self.tree.column("status", width=70, anchor="center", stretch=False)
        self.tree.column("url", width=800, anchor="w")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_selected)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(8, 4), relief="sunken")
        status.pack(fill="x", side="bottom")

    def _int_field(self, parent, label, var, width):
        ttk.Label(parent, text=label).pack(side="left", padx=(6, 2))
        ttk.Spinbox(parent, from_=1, to=10000, textvariable=var, width=width).pack(side="left")

    def _float_field(self, parent, label, var, width):
        ttk.Label(parent, text=label).pack(side="left", padx=(6, 2))
        ttk.Spinbox(
            parent, from_=0.0, to=60.0, increment=0.1,
            textvariable=var, width=width,
        ).pack(side="left")

    def _start(self):
        if self._crawler_thread and self._crawler_thread.is_alive():
            return
        seed = self.seed_var.get().strip()
        if not seed:
            self.status_var.set("Enter a seed URL.")
            return
        if not seed.startswith(("http://", "https://")):
            seed = "https://" + seed
            self.seed_var.set(seed)

        config = CrawlConfig(
            seeds=[seed],
            max_depth=self.depth_var.get(),
            max_pages=self.max_pages_var.get(),
            concurrency=self.workers_var.get(),
            same_domain=self.same_domain_var.get(),
            respect_robots=self.robots_var.get(),
            rate_limit_sec=self.rate_var.get(),
        )
        pipeline_cls = next(p for p in AVAILABLE_PIPELINES if p.name == self.pipeline_var.get())
        pipeline = pipeline_cls()

        self.tree.delete(*self.tree.get_children())
        self._row_urls = []
        self._counts = {"crawled": 0, "enqueued": 0, "skipped": 0, "errors": 0}
        self._event_queue = queue.Queue()
        self._crawler = Crawler(config, pipeline, on_event=self._event_queue.put)

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("Running…")

        self._crawler_thread = threading.Thread(target=self._crawler.run, daemon=True)
        self._crawler_thread.start()
        self.after(100, self._poll_events)

    def _stop(self):
        if self._crawler:
            self._crawler.stop()
        self.status_var.set("Stopping…")

    def _poll_events(self):
        drained = 0
        while drained < 200:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
            drained += 1

        if self._crawler_thread and self._crawler_thread.is_alive():
            self._update_status()
            self.after(100, self._poll_events)
        else:
            self._update_status(final=True)
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _handle_event(self, event):
        if event.kind == "page":
            self._counts["crawled"] += 1
            self.tree.insert("", "end", values=(event.depth, event.status_code, event.url))
            self._row_urls.append(event.url)
        elif event.kind == "enqueued":
            self._counts["enqueued"] += 1
        elif event.kind == "skipped":
            self._counts["skipped"] += 1
        elif event.kind == "error":
            self._counts["errors"] += 1
            self.tree.insert("", "end", values=(event.depth or "", "ERR", f"{event.url} — {event.message}"))
            self._row_urls.append(event.url or "")

    def _update_status(self, final=False):
        c = self._counts
        pending = len(self._crawler._frontier) if self._crawler else 0
        prefix = "Done" if final else "Running"
        self.status_var.set(
            f"{prefix}  |  crawled {c['crawled']}  queued {pending}  "
            f"enqueued {c['enqueued']}  skipped {c['skipped']}  errors {c['errors']}"
        )

    def _open_selected(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        index = self.tree.index(selection[0])
        if 0 <= index < len(self._row_urls) and self._row_urls[index]:
            webbrowser.open(self._row_urls[index])


if __name__ == "__main__":
    CrawlerApp().mainloop()
