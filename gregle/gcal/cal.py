import datetime
from collections.abc import Iterator

from gregle.gcal import ft

from ..event import Diff, Event
from ..log import log
from .event import EventView
from .service import API, Calendar


def get_calendar(api: API, name: str) -> Calendar:
    page_token: str | None = None
    while True:
        log.info(f"Request: Calendars - {name}")
        res: dict = api.calendarList().list(pageToken=page_token).execute()
        for cal in res["items"]:
            if cal["summary"].lower() == name.lower():
                return cal["id"]
        if (page_token := res.get("nextPageToken")) is None:
            break
    raise ValueError(f"No Calendar {name}")


def get_events(api: API, calendar_id: Calendar, start: datetime.date, end: datetime.date) -> Iterator[EventView]:
    page_token: str | None = None

    while True:
        log.info(f"Request: Events {start} - {end}")
        res: dict = (
            api.events()
            .list(
                calendarId=calendar_id,
                timeMin=start.strftime(ft.RFC3339_DATETIME_UTC),
                timeMax=end.strftime(ft.RFC3339_DATETIME_UTC),
                pageToken=page_token,
            )
            .execute()
        )
        for event in res["items"]:
            yield EventView(event)
        if (page_token := res.get("nextPageToken")) is None:
            break


DRY_RUN: bool = False

if not DRY_RUN:

    def post_create(api: API, calendar: Calendar, event: EventView) -> str:
        eid = api.events().insert(calendarId=calendar, body=event.raw).execute()["id"]
        event.raw["id"] = eid
        return eid

    def post_update(api: API, calendar: Calendar, event_from: Event, event_to: EventView) -> None:
        if (eid := event_from.id()) is None:
            return
        event_to.raw["id"] = eid
        api.events().update(calendarId=calendar, eventId=eid, body=event_to.raw).execute()

    def post_delete(api: API, calendar: Calendar, event_id: str) -> None:
        api.events().delete(calendarId=calendar, eventId=event_id).execute()

else:

    def post_create(api: API, calendar: Calendar, event: EventView) -> str:
        return "<ID>"

    def post_update(api: API, calendar: Calendar, event_from: Event, event_to: EventView) -> None:
        pass

    def post_delete(api: API, calendar: Calendar, event_id: str) -> None:
        pass


def process_diff(api: API, calendar: Calendar, change: Diff[Event]) -> None:
    match change:
        case ("create", e):
            post_create(api, calendar, EventView.from_event(e))
        case ("delete", e):
            e_id = e.id()
            if e_id is None:
                return
            post_delete(api, calendar, e_id)
        case ("update", (e_from, e_to)):
            post_update(api, calendar, e_from, EventView.from_event(e_to))
