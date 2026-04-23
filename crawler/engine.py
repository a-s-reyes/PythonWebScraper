import threading
from concurrent.futures import ThreadPoolExecutor

from .fetcher import USER_AGENT, RateLimiter, make_session
from .filters import is_allowed, normalize, registrable_host
from .frontier import Frontier
from .models import CrawlEvent, Page
from .parser import extract_links
from .robots import RobotsCache


class Crawler:
    def __init__(self, config, pipeline, on_event=None):
        self.config = config
        self.pipeline = pipeline
        self.on_event = on_event or (lambda e: None)

        self._frontier = Frontier()
        self._session = make_session()
        self._rate_limiter = RateLimiter(config.rate_limit_sec)
        self._robots = RobotsCache(USER_AGENT) if config.respect_robots else None

        self._seed_hosts = {registrable_host(s) for s in config.seeds}
        self._stop = threading.Event()
        self._pages_crawled = 0
        self._counter_lock = threading.Lock()
        self._active_workers = 0
        self._active_lock = threading.Lock()

    def stop(self):
        self._stop.set()
        self._frontier.close()

    def run(self):
        for seed in self.config.seeds:
            self._frontier.add(normalize(seed), 0)

        with ThreadPoolExecutor(max_workers=self.config.concurrency) as ex:
            for _ in range(self.config.concurrency):
                ex.submit(self._worker)

        self.pipeline.close()
        self.on_event(CrawlEvent(kind="done", message=f"{self._pages_crawled} pages"))

    def _worker(self):
        while not self._stop.is_set():
            if self._reached_limit():
                self._frontier.close()
                return

            item = self._frontier.pop(timeout=0.5)
            if item is None:
                # No work right now. If no other worker is busy either, we're done.
                with self._active_lock:
                    if self._active_workers == 0 and len(self._frontier) == 0:
                        self._frontier.close()
                        return
                continue

            url, depth = item
            with self._active_lock:
                self._active_workers += 1
            try:
                self._process(url, depth)
            finally:
                with self._active_lock:
                    self._active_workers -= 1

    def _reached_limit(self) -> bool:
        with self._counter_lock:
            return self._pages_crawled >= self.config.max_pages

    def _process(self, url: str, depth: int):
        if self._robots and not self._robots.allowed(url):
            self.on_event(CrawlEvent(kind="skipped", url=url, message="robots.txt"))
            return

        self._rate_limiter.wait()
        if self._stop.is_set():
            return

        try:
            resp = self._session.get(url, timeout=self.config.timeout_sec, allow_redirects=True)
        except Exception as e:
            self.on_event(CrawlEvent(kind="error", url=url, depth=depth, message=str(e)))
            return

        content_type = resp.headers.get("Content-Type", "")
        is_html = "html" in content_type.lower()
        html = resp.text if is_html else None

        page = Page(
            url=url,
            depth=depth,
            status_code=resp.status_code,
            content_type=content_type,
            html=html,
        )

        with self._counter_lock:
            self._pages_crawled += 1

        try:
            self.pipeline.process(page)
        except Exception as e:
            self.on_event(CrawlEvent(kind="error", url=url, message=f"pipeline: {e}"))

        self.on_event(CrawlEvent(
            kind="page", url=url, depth=depth, status_code=resp.status_code
        ))

        if is_html and depth < self.config.max_depth and resp.ok:
            page.links = extract_links(html, resp.url)
            for link in page.links:
                ok, _ = is_allowed(link, self.config, self._seed_hosts)
                if not ok:
                    continue
                if self._frontier.add(link, depth + 1):
                    self.on_event(CrawlEvent(kind="enqueued", url=link, depth=depth + 1))
