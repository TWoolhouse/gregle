from collections import defaultdict
from collections.abc import Iterable, Iterator
from typing import Literal

from ..event import Diff
from .event import EventSchedule, GroupID


def changes(a: Iterable[EventSchedule], b: Iterable[EventSchedule]) -> Iterator[Diff[EventSchedule]]:
    tbl: dict[GroupID, list[tuple[Literal["a", "b"], EventSchedule]]] = defaultdict(list)
    for e in a:
        tbl[e.instance.group()].append(("a", e))
    for e in b:
        tbl[e.instance.group()].append(("b", e))

    for vals in tbl.values():
        match vals:
            case [("a", lhs), ("b", rhs)]:
                if _is_diff(lhs, rhs):
                    yield ("update", (lhs, rhs))
            case [("a", e)]:
                yield ("delete", e)
            case [("b", e)]:
                yield ("create", e)
            case [("a", a_first), *a_rest, ("b", rhs)]:
                lhs = EventSchedule.combine(a_first, *(i[1] for i in a_rest), eid=a_first.id())
                for e in a_rest:
                    yield ("delete", e[1])
                if _is_diff(lhs, rhs):
                    yield ("update", (lhs, rhs))
                raise NotImplementedError
            case x:
                raise ValueError(x)


def _is_diff(a: EventSchedule, b: EventSchedule) -> bool:
    return a.on_dates != b.on_dates or a.instance != b.instance
