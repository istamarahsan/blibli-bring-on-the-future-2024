from typing import Protocol, Callable
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace


class DatetimeProvider(Protocol):
    def now(self) -> datetime:
        pass

    @staticmethod
    def FromTimezone(tz: timezone) -> "DatetimeProvider":
        return SimpleNamespace(now=lambda: datetime.now(tz))

    @staticmethod
    def FromOffsetHours(offset: int) -> "DatetimeProvider":
        return SimpleNamespace(
            now=lambda: datetime.now(timezone(timedelta(hours=offset)))
        )

    @staticmethod
    def FromFunc(f: Callable[[], datetime]) -> "DatetimeProvider":
        return SimpleNamespace(now=f)
