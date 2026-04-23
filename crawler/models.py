from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrawlConfig:
    seeds: list
    max_depth: int = 3
    max_pages: int = 100
    concurrency: int = 4
    same_domain: bool = True
    respect_robots: bool = True
    rate_limit_sec: float = 0.5
    timeout_sec: float = 10.0
    allowed_schemes: set = field(default_factory=lambda: {"http", "https"})
    # Common non-HTML extensions we skip by default
    skip_extensions: set = field(default_factory=lambda: {
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv",
        ".css", ".js", ".xml", ".json",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    })


@dataclass
class Page:
    url: str
    depth: int
    status_code: int
    content_type: Optional[str]
    html: Optional[str]
    links: list = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CrawlEvent:
    kind: str  # "page", "error", "enqueued", "skipped", "done"
    url: Optional[str] = None
    depth: Optional[int] = None
    status_code: Optional[int] = None
    message: Optional[str] = None
