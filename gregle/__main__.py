import datetime
import logging.config
from collections.abc import Iterable, Iterator
from pathlib import Path
from pprint import pp

import gregle


def log_config() -> None:
    LOG = (Path(__name__).parent / "log").resolve()
    LOG.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "brief": {
                    "format": "[%(levelname)s] %(name)s : %(message)s",
                },
                "verbose": {
                    "format": "%(asctime)s [%(levelname)-8s] %(name)s : %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "brief",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": f"{LOG}/gregle.{now}.log",
                    "mode": "w",
                    "formatter": "verbose",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console", "file"],
            },
            "disable_existing_loggers": False,
        }
    )


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


def gcal_to_lu(
    api: gregle.gcal.service.API,
    calendar: gregle.gcal.service.Calendar,
    events: Iterable[gregle.gcal.Event],
) -> Iterator[gregle.lu.Events]:
    failed: list[gregle.gcal.Event] = []
    for event in events:
        try:
            yield gregle.lu.Events.from_event(event)
        except Exception as exc:
            gregle.log.error("Failed to convert event %s", event, exc_info=exc)
            failed.append(event)
    for event in failed:
        gregle.log.info("Deleting corrupt event %s", event)
        if eid := event.id():
            try:
                gregle.gcal.cal.post_delete(api, calendar, eid)
            except Exception as exc:
                gregle.log.error("Failed to delete event %s", event, exc_info=exc)
        else:
            gregle.log.error("Event %s has no ID", event)


def main() -> None:
    log_config()
    try:
        local, date_range = events_local()
        with gregle.gcal.service.calendar() as api:
            calendar = gregle.gcal.cal.get_calendar(api, "Timetable")
            remote = events_remote(api, calendar, date_range)
            for change in gregle.lu.diff(list(gcal_to_lu(api, calendar, remote)), local):
                pp(change)
                gregle.gcal.cal.process_diff(api, calendar, change)
    except Exception as e:
        gregle.log.fatal("Unhandled exception", exc_info=e)
        raise


main()
