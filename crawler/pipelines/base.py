from typing import Protocol, runtime_checkable


@runtime_checkable
class Pipeline(Protocol):
    """Contract every pipeline must satisfy.

    Pipelines receive each successfully crawled Page. Implementations must
    be thread-safe — workers call `process` concurrently.
    """

    name: str

    def process(self, page) -> None: ...

    def close(self) -> None: ...
