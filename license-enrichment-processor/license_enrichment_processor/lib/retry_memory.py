from packageurl import PackageURL
from datetime import datetime
from typing import Protocol


class RetryMemory(Protocol):
    def recall(self, purl: PackageURL) -> datetime | None:
        pass

    def remember(self, purl: PackageURL, timestamp: datetime):
        pass


class InMemoryRetryMemory:

    memory: dict[str, datetime]

    def __init__(self):
        self.memory = dict()

    def recall(self, purl: PackageURL) -> datetime | None:
        return (
            self.memory[purl.to_string()] if purl.to_string() in self.memory else None
        )

    def remember(self, purl: PackageURL, timestamp: datetime):
        self.memory[purl.to_string()] = timestamp
