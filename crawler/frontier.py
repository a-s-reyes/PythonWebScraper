import threading
from collections import deque
from typing import Optional


class Frontier:
    """Thread-safe URL queue paired with a visited set.

    `add` returns False if the URL was already seen, True if enqueued.
    `pop` blocks until a URL is available or the frontier is closed.
    """

    def __init__(self):
        self._queue = deque()
        self._visited = set()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._closed = False

    def add(self, url: str, depth: int) -> bool:
        with self._not_empty:
            if url in self._visited or self._closed:
                return False
            self._visited.add(url)
            self._queue.append((url, depth))
            self._not_empty.notify()
            return True

    def pop(self, timeout: Optional[float] = None):
        with self._not_empty:
            while not self._queue and not self._closed:
                if not self._not_empty.wait(timeout=timeout):
                    return None
            if self._queue:
                return self._queue.popleft()
            return None

    def close(self):
        with self._not_empty:
            self._closed = True
            self._not_empty.notify_all()

    def __len__(self):
        with self._lock:
            return len(self._queue)

    @property
    def visited_count(self):
        with self._lock:
            return len(self._visited)
