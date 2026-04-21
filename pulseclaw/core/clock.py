from datetime import UTC, datetime


def now() -> datetime:
    """UTC now. Injectable for tests by monkeypatching this module."""
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()
