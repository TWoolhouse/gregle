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


def post_create(api: API, calendar: Calendar, event: EventView, *, dry_run: bool) -> str:
    if dry_run:
        return event.id() or "dry-run"
    eid = api.events().insert(calendarId=calendar, body=event.raw).execute()["id"]
    event.raw["id"] = eid
    return eid


def post_update(api: API, calendar: Calendar, event_from: Event, event_to: EventView, *, dry_run: bool) -> None:
    if (eid := event_from.id()) is None:
        return
    event_to.raw["id"] = eid
    if dry_run:
        return
    api.events().update(calendarId=calendar, eventId=eid, body=event_to.raw).execute()


def post_delete(api: API, calendar: Calendar, event_id: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    api.events().delete(calendarId=calendar, eventId=event_id).execute()


def process_diff(api: API, calendar: Calendar, change: Diff[Event], *, dry_run: bool) -> None:
    match change:
        case ("create", e):
            post_create(api, calendar, EventView.from_event(e), dry_run=dry_run)
        case ("delete", e):
            e_id = e.id()
            if e_id is None:
                return
            post_delete(api, calendar, e_id, dry_run=dry_run)
        case ("update", (e_from, e_to)):
            post_update(api, calendar, e_from, EventView.from_event(e_to), dry_run=dry_run)
