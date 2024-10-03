import datetime
from pprint import pp

import gregle


def events_remote(
    api: gregle.gcal.service.API,
    calendar: str,
    date_range: tuple[datetime.date, datetime.date],
) -> list[gregle.gcal.Event]:
    return list(gregle.gcal.cal.get_events(api, calendar, *date_range))


def events_local() -> tuple[list[gregle.lu.Events], tuple[datetime.date, datetime.date]]:
    events, dates = gregle.lu.events()
    events.sort(key=lambda e: e.first.start)
    return events, dates


def main() -> None:
    local, date_range = events_local()
    with gregle.gcal.service.calendar() as api:
        calendar = gregle.gcal.cal.get_calendar(api, "Timetable")
        remote = events_remote(api, calendar, date_range)
        for change in gregle.lu.diff([gregle.lu.Events.from_event(e) for e in remote], local):
            pp(change)
            gregle.gcal.cal.process_diff(api, calendar, change)
