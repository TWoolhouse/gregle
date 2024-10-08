from collections import defaultdict
from collections.abc import Iterable, Iterator
from typing import Literal

from ..event import Diff
from .event import EventGroup, GroupID


def changes(a: Iterable[EventGroup], b: Iterable[EventGroup]) -> Iterator[Diff[EventGroup]]:
    tbl: dict[GroupID, list[tuple[Literal["a", "b"], EventGroup]]] = defaultdict(list)
    for e in a:
        tbl[e.first.group()].append(("a", e))
    for e in b:
        tbl[e.first.group()].append(("b", e))

    for vals in tbl.values():
        match vals:
            case [("a", lhs), ("b", rhs)]:
                if _is_diff(lhs, rhs):
                    yield ("update", (lhs, rhs))
            case [("a", e)]:
                yield ("delete", e)
            case [("b", e)]:
                yield ("create", e)
            case x:
                raise ValueError(x)


def _is_diff(a: EventGroup, b: EventGroup) -> bool:
    return a.on_dates != b.on_dates or a.first != b.first
