import os
from urllib.parse import urldefrag, urlparse, urlunparse


def normalize(url: str) -> str:
    """Canonicalize URL for dedup: drop fragment, lowercase host, strip default port."""
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if (scheme == "http" and netloc.endswith(":80")) or (scheme == "https" and netloc.endswith(":443")):
        netloc = netloc.rsplit(":", 1)[0]
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower()


def registrable_host(url: str) -> str:
    """Strip leading www. for same-domain comparison."""
    host = host_of(url)
    return host[4:] if host.startswith("www.") else host


def is_allowed(url: str, config, seed_hosts: set) -> tuple[bool, str]:
    """Apply scope filters. Returns (allowed, reason_if_not)."""
    parsed = urlparse(url)
    if parsed.scheme not in config.allowed_schemes:
        return False, f"scheme {parsed.scheme}"
    if not parsed.netloc:
        return False, "no host"
    if config.same_domain and registrable_host(url) not in seed_hosts:
        return False, "off-domain"
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext and ext in config.skip_extensions:
        return False, f"ext {ext}"
    return True, ""
