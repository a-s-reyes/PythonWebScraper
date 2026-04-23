import threading
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsCache:
    """Per-host robots.txt cache. Fetch failures default to allow."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._cache = {}
        self._lock = threading.Lock()

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._get(host)
        if parser is None:
            return True
        try:
            return parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def _get(self, host: str):
        with self._lock:
            if host in self._cache:
                return self._cache[host]
        rp = RobotFileParser()
        rp.set_url(f"{host}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        with self._lock:
            self._cache[host] = rp
        return rp
