import abc
import datetime
import itertools
from typing import Iterable, Literal, Self


class Event(abc.ABC):
    @abc.abstractmethod
    def id(self) -> str | None:
        """Optional unique identifier for the event."""
        ...

    @abc.abstractmethod
    def title(self) -> str:
        """The title of the event."""
        ...

    @abc.abstractmethod
    def description(self) -> str:
        """The description of the event."""
        ...

    @abc.abstractmethod
    def address(self) -> str:
        """Real world location of the event."""
        ...

    @abc.abstractmethod
    def time_start(self) -> datetime.datetime:
        """The start datetime of the first event occurrence."""
        ...

    @abc.abstractmethod
    def time_delta(self) -> datetime.timedelta:
        """The duration of the event."""
        ...

    @abc.abstractmethod
    def occurrences(self) -> Iterable[datetime.date]:
        """The dates of the event occurrences.

        This does NOT include the start date."""
        ...

    @classmethod
    @abc.abstractmethod
    def from_event(cls, other: "Event") -> Self:
        """Convert another event to this event type."""
        ...


type Create[E: Event] = E
type Delete[E: Event] = E
type Update[E: Event] = tuple[E, E]
type Diff[E: Event] = (
    tuple[Literal["create"], Create[E]] | tuple[Literal["delete"], Delete[E]] | tuple[Literal["update"], Update[E]]
)


def datespan(events: Iterable[Event]) -> tuple[datetime.date, datetime.date]:
    """Get the date range of the events.

    Returns:
        A tuple in the format (start, end]."""
    dates = {date for event in events for date in itertools.chain((event.time_start().date(),), event.occurrences())}
    return min(dates), max(dates) + datetime.timedelta(days=1)
