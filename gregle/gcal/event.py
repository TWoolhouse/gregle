import contextlib
import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Self
from zoneinfo import ZoneInfo

from gregle import tz
from gregle.gcal import ft

from ..event import Event
from ..log import log


def parse_time(time: dict[str, str]) -> datetime.datetime:
    try:
        try:
            return datetime.datetime.strptime(time["dateTime"], ft.RFC3339_DATETIME)
        except ValueError:
            t = time["dateTime"][:-3] + time["dateTime"][-2:]
            return datetime.datetime.strptime(t, ft.RFC3339_DATETIME)
    except ValueError:
        info = ZoneInfo(key) if (key := time.get("timeZone", None)) is not None else tz.DEFAULT
        return datetime.datetime.strptime(time["dateTime"], ft.RFC3339_DATETIME_LOCAL).astimezone(info)


@dataclass(frozen=True)
class EventView(Event):
    raw: dict[str, Any]

    def id(self) -> str | None:
        return self.raw["id"]

    def title(self) -> str:
        return self.raw["summary"].strip()

    def description(self) -> str:
        return self.raw["description"].strip()

    def address(self) -> str:
        return self.raw["location"].strip()

    def time_start(self) -> datetime.datetime:
        return parse_time(self.raw["start"])

    def time_end(self) -> datetime.datetime:
        return parse_time(self.raw["end"])

    def time_delta(self) -> datetime.timedelta:
        return self.time_end() - self.time_start()

    def occurrences(self) -> Iterable[datetime.date]:
        dates = []
        for rule in self.raw.get("recurrence", []):
            ty, rule = rule.split(";")
            match ty:
                case "RDATE":
                    segments = rule.split(":")
                    dates.extend(
                        datetime.datetime.strptime(d, ft.RFC5545_DATETIME_LOCAL).date() for d in segments[-1].split(",")
                    )
                case _:
                    log.error("Recurrence Rule Type '%s' is not supported", ty)
        dates.sort()
        return dates

    @classmethod
    def from_event(cls, other: "Event") -> Self:
        tzinfo = other.time_start().tzinfo
        if tzinfo is None:
            raise ValueError("Event must have a timezone")
        tz: str = tzinfo.key  # type: ignore
        start = other.time_start().time()
        occurrences = other.occurrences()

        obj = {
            "id": other.id(),
            "summary": other.title(),
            "description": other.description(),
            "start": {
                "dateTime": other.time_start().strftime(ft.RFC3339_DATETIME_LOCAL),
                "timeZone": tz,
            },
            "end": {
                "dateTime": (other.time_start() + other.time_delta()).strftime(ft.RFC3339_DATETIME_LOCAL),
                "timeZone": tz,
            },
            "recurrence": [
                f"RDATE;TZID={tz}:"
                + ",".join(
                    datetime.datetime.combine(d, start, ZoneInfo(tz)).strftime(ft.RFC5545_DATETIME_LOCAL)
                    for d in occurrences
                )
            ]
            if occurrences
            else [],
        }
        with contextlib.suppress(KeyError):
            obj["location"] = other.address()
        return cls(obj)


Event.register(EventView)
