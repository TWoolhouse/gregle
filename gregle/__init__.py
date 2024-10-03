import datetime
from pprint import pp

from gregle.lu import diff

from .gcal import cal, service
from .gcal.event import EventView
from .lu.event import EventGroup
from .lu.ri import events as get_events_local


def events_remote(
    api: service.API,
    calendar: str,
    date_range: tuple[datetime.date, datetime.date],
) -> list[EventView]:
    return list(cal.get_events(api, calendar, *date_range))


def events_local() -> tuple[list[EventGroup], tuple[datetime.date, datetime.date]]:
    events, dates = get_events_local()
    events.sort(key=lambda e: e.first.start)
    return events, dates


def main() -> None:
    local, date_range = events_local()
    with service.calendar() as api:
        calendar = cal.fetch_id(api, "Timetable")
        remote = events_remote(api, calendar, date_range)
        for change in diff.changes([EventGroup.from_event(e) for e in remote], local):
            pp(change)
            cal.process_change(api, calendar, change)


main()
