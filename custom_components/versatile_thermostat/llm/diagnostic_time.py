"""Strict timestamps for the read-only LLM diagnostic tools."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


_ISO_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z",
    re.ASCII,
)


@dataclass(frozen=True, order=True)
class ExactTimestamp:
    """UTC instant with arbitrary fractional precision."""

    second: datetime
    fraction: str

    @classmethod
    def from_datetime(cls, value: datetime) -> "ExactTimestamp":
        value = value.astimezone(timezone.utc)
        return cls(value.replace(microsecond=0), f"{value.microsecond:06d}".rstrip("0"))

    def floor(self) -> datetime:
        return self.second + timedelta(microseconds=int((self.fraction + "000000")[:6]))

    def ceil(self) -> datetime:
        floor = self.floor()
        return floor + timedelta(microseconds=1) if any(c != "0" for c in self.fraction[6:]) else floor

    def minus_hour(self) -> "ExactTimestamp":
        return ExactTimestamp(self.second - timedelta(hours=1), self.fraction)

    def isoformat(self) -> str:
        base = self.second.isoformat().replace("+00:00", "")
        return base + (f".{self.fraction}" if self.fraction else "") + "Z"


def parse_timestamp(value: str) -> ExactTimestamp:
    """Parse an explicitly offset timestamp without discarding fractional digits."""
    if not isinstance(value, str) or not _ISO_TIMESTAMP.fullmatch(value):
        raise ValueError("Timestamp must be ISO 8601 with an explicit offset")
    if not value.endswith("Z") and int(value[-2:]) > 59:
        raise ValueError("Invalid offset minutes")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp must include an offset")
    fraction = value[19:].split("Z", 1)[0].split("+", 1)[0].split("-", 1)[0]
    return ExactTimestamp(parsed.astimezone(timezone.utc).replace(microsecond=0), fraction.removeprefix(".").rstrip("0"))


def utc_timestamp(value: datetime) -> str:
    """Serialize an aware datetime as UTC."""
    if value.utcoffset() is None:
        raise ValueError("Timestamp must include an offset")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")