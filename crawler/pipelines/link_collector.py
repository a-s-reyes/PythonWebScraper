import threading


class LinkCollectorPipeline:
    """Default pipeline: records every crawled URL. No extraction."""

    name = "Link Collector"

    def __init__(self):
        self.pages = []
        self._lock = threading.Lock()

    def process(self, page):
        with self._lock:
            self.pages.append((page.url, page.depth, page.status_code))

    def close(self):
        pass
