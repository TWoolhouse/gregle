import abc
import datetime
import io
import itertools
from dataclasses import dataclass
from pprint import pp
from typing import Any, Iterable, Literal, Self


@dataclass
class E:
    """Information about the event."""

    id: str | None
    title: str | None
    description: str | None
    address: str | None
    time_start: datetime.time
    time_delta: datetime.timedelta
    dates: Iterable[datetime.date]

    @classmethod
    def from_event(cls, event: "Event") -> Self:
        """Convert an event to information."""

        def try_getattr(obj: object, attr: str, exc_type: type[Exception] = AttributeError) -> Any | None:
            """Get an attribute from an object, returning None if it doesn't exist."""
            try:
                return getattr(obj, attr)()
            except exc_type:
                return None

        # FIXME: Nicely format the events
        return cls(
            id=try_getattr(event, "id"),
            title=try_getattr(event, "title"),
            description=try_getattr(event, "description"),
            address=try_getattr(event, "address", KeyError),
            time_start=event.time_start().time(),
            time_delta=event.time_delta(),
            dates=[event.time_start().date()] + list(event.occurrences()),
        )


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

    def pretty(self) -> str:
        """Return a pretty string representation of the event."""
        buf = io.StringIO()
        pp(E.from_event(self), stream=buf, indent=4, width=160, compact=False)
        return buf.getvalue()


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
