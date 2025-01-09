import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from gregle import tz
from gregle.lu.address import address as address_of_room

from ..event import Event

type Slot = tuple[datetime.time, datetime.timedelta]
"""Unique ID of a time slot within a week.
- Start time
- Duration
"""

type GroupID = tuple[Slot, tuple[str, ...], tuple[str, ...], tuple[str, ...], str]
"""Data shared between recurring events.
- Time slot
- Module code
- Rooms
- Lecturers
- Content type
"""


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class EventInstance:
    module_codes: tuple[str, ...]
    module_name: str
    rooms: tuple[str, ...]
    lecturers: tuple[str, ...]
    content_type: str
    start: datetime.time
    duration: datetime.timedelta

    def slot(self) -> Slot:
        return (self.start, self.duration)

    def group(self) -> GroupID:
        return (
            self.slot(),
            self.module_codes,
            self.rooms,
            self.lecturers,
            self.content_type,
        )


@dataclass(slots=True)
class EventSchedule(Event):
    _id: str | None
    instance: EventInstance
    on_dates: list[datetime.date]

    def id(self) -> str | None:
        return self._id

    def title(self) -> str:
        return f"{self.instance.module_name} - {".".join(self.instance.module_codes)}"

    def description(self) -> str:
        return "\n".join(
            (
                ", ".join(self.instance.module_codes),
                self.instance.module_name,
                ", ".join(self.instance.rooms),
                ", ".join(self.instance.lecturers),
                self.instance.content_type,
            )
        )

    def address(self) -> str:
        exception: KeyError | None = None
        for room in self.instance.rooms:
            try:
                return address_of_room(room)
            except KeyError as exc:
                exception = exc
                continue
        raise KeyError("No address found for any room") from exception

    def time_start(self) -> datetime.datetime:
        return datetime.datetime.combine(self.on_dates[0], self.instance.start, tz.DEFAULT)

    def time_delta(self) -> datetime.timedelta:
        return self.instance.duration

    def occurrences(self) -> Iterable[datetime.date]:
        return self.on_dates[1:]

    @classmethod
    def from_event(cls, other: Event) -> Self:
        data = other.description().strip().split("\n")
        data += [""] * 5
        module_codes, module_name, rooms, lecturers, content_type = data[:5]
        start = other.time_start().astimezone(tz.DEFAULT)
        event = EventInstance(
            tuple(sorted(filter(None, module_codes.split(", ")))),
            module_name,
            tuple(sorted(filter(None, rooms.split(", ")))),
            tuple(sorted(filter(None, lecturers.split(", ")))),
            content_type,
            start.time(),
            other.time_delta(),
        )

        return cls(other.id(), event, [start.date()] + list(other.occurrences()))

    @classmethod
    def combine(cls, *events: Self, eid: str | None = None) -> Self:
        assert len(events), "No events to combine"
        assert all(
            e.instance.group() == events[0].instance.group() for e in events[1:]
        ), "Events do not share the same group"
        on_dates = sorted({date for event in events for date in event.on_dates})
        return cls(
            eid,
            events[0].instance,
            on_dates,
        )
