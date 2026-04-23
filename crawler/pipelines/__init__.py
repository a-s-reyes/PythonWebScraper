from .base import Pipeline
from .link_collector import LinkCollectorPipeline

AVAILABLE = [LinkCollectorPipeline]
BY_NAME = {p.name: p for p in AVAILABLE}

__all__ = ["Pipeline", "LinkCollectorPipeline", "AVAILABLE", "BY_NAME"]
