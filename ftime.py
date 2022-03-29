from zoneinfo import ZoneInfo
import datetime

TZ = ZoneInfo("Europe/London")

ISO_SHORT = "%Y%m%dT%H%M%S"
ISO_LONG = "%Y-%m-%dT%H:%M:%S"

def fmt_tz(timestamp: str) -> str:
	return f"{timestamp[:-2]}:{timestamp[-2:]}"
def unfmt_tz(timestamp: str) -> str:
	return f"{timestamp[:-3]}{timestamp[-2:]}"

def fmt(date_time: datetime.datetime, fmt=ISO_LONG) -> str:
	if date_time.tzinfo is None:
		return date_time.strftime(fmt+"Z")
	return fmt_tz(date_time.strftime(fmt+"%z"))

def read(timestamp: str, fmt=ISO_LONG, tz=False) -> datetime.datetime:
	if tz:
		try:
			return datetime.datetime.strptime(unfmt_tz(timestamp), fmt+"%z")
		except ValueError as e1:
			try:
				return datetime.datetime.strptime(timestamp, fmt+"Z")
			except ValueError as e2:
				return datetime.datetime.strptime(timestamp, fmt)
	else:
		dt = read(timestamp, fmt=fmt, tz=True)
		return datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)
