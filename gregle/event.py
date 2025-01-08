import abc
import datetime
import itertools
from typing import Iterable, Literal, Self


class Event(abc.ABC):
    @abc.abstractmethod
    def id(self) -> str | None: ...

    @abc.abstractmethod
    def title(self) -> str: ...
    @abc.abstractmethod
    def description(self) -> str: ...
    @abc.abstractmethod
    def address(self) -> str: ...
    @abc.abstractmethod
    def time_start(self) -> datetime.datetime: ...
    @abc.abstractmethod
    def time_delta(self) -> datetime.timedelta: ...
    @abc.abstractmethod
    def occurrences(self) -> Iterable[datetime.date]: ...

    @classmethod
    @abc.abstractmethod
    def from_event(cls, other: "Event") -> Self: ...


type Create[E: Event] = E
type Delete[E: Event] = E
type Update[E: Event] = tuple[E, E]
type Diff[E: Event] = (
    tuple[Literal["create"], Create[E]] | tuple[Literal["delete"], Delete[E]] | tuple[Literal["update"], Update[E]]
)


def datespan(events: Iterable[Event]) -> tuple[datetime.date, datetime.date]:
    dates = {date for event in events for date in itertools.chain((event.time_start().date(),), event.occurrences())}
    return min(dates), max(dates) + datetime.timedelta(days=1)
