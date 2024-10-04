import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from gregle.lu.address import address as address_of_room

from ..event import Event

type Slot = tuple[int, datetime.time, datetime.timedelta]
"""ID unique a slot of time within a week.
- Weekday
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
class EventRaw:
    module_codes: tuple[str, ...]
    module_name: str
    rooms: tuple[str, ...]
    lecturers: tuple[str, ...]
    content_type: str
    start: datetime.datetime
    duration: datetime.timedelta

    def slot(self) -> Slot:
        return (self.start.weekday(), self.start.time(), self.duration)

    def group(self) -> GroupID:
        return (
            self.slot(),
            self.module_codes,
            self.rooms,
            self.lecturers,
            self.content_type,
        )

    def with_date(self, date: datetime.date) -> Self:
        return self.__class__(
            self.module_codes,
            self.module_name,
            self.rooms,
            self.lecturers,
            self.content_type,
            datetime.datetime.combine(date, self.start.time(), self.start.tzinfo),
            self.duration,
        )


@dataclass(slots=True)
class EventGroup(Event):
    _id: str | None
    first: EventRaw
    on_dates: list[datetime.date]

    def id(self) -> str | None:
        return self._id

    def title(self) -> str:
        return f"{self.first.module_name} - {".".join(self.first.module_codes)}"

    def description(self) -> str:
        return "\n".join(
            (
                ", ".join(self.first.module_codes),
                self.first.module_name,
                ", ".join(self.first.rooms),
                ", ".join(self.first.lecturers),
                self.first.content_type,
            )
        )

    def address(self) -> str:
        return address_of_room(self.first.rooms[0])

    def time_start(self) -> datetime.datetime:
        return self.first.start

    def time_delta(self) -> datetime.timedelta:
        return self.first.duration

    def occurrences(self) -> Iterable[datetime.date]:
        return self.on_dates

    @classmethod
    def from_event(cls, other: Event) -> Self:
        module_codes, module_name, rooms, lecturers, content_type = other.description().strip().split("\n")
        event = EventRaw(
            tuple(sorted(module_codes.split(", "))),
            module_name,
            tuple(sorted(rooms.split(", "))),
            tuple(sorted(lecturers.split(", "))),
            content_type,
            other.time_start(),
            other.time_delta(),
        )

        return cls(other.id(), event, list(other.occurrences()))
