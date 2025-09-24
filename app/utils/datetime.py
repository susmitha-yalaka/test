from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def now_ms_ist() -> int:
    """Return current IST time in milliseconds."""
    return int(datetime.now(IST).timestamp() * 1000)


def now_str_ist() -> str:
    """Return current IST time as a readable string with ms."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
