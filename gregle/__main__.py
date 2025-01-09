import argparse
import datetime
import logging.config
from collections.abc import Iterable, Iterator
from pathlib import Path
from pprint import pp

import gregle


def log_config(level: int) -> None:
    LOG = (Path(__name__).parent / "log").resolve()
    LOG.mkdir(exist_ok=True)
    LEVELS = ["INFO", "DEBUG"]
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
                "level": LEVELS[min(level, len(LEVELS) - 1)],
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


def events_local(cache: bool = True) -> tuple[list[gregle.lu.Events], tuple[datetime.date, datetime.date]]:
    gregle.log.info("Loading events from LU timetable...")
    events = gregle.lu.events(True) if cache else gregle.lu.events.write(False)
    gregle.log.info("Loaded %d LU events over %d dates", len(events), sum(len(e.on_dates) for e in events))
    dates = gregle.event.datespan(events)
    gregle.log.info("LU events span %s to %s", *dates)
    events.sort(key=lambda e: e.time_start())
    return events, dates


def gcal_to_lu(
    api: gregle.gcal.service.API,
    calendar: gregle.gcal.service.Calendar,
    events: Iterable[gregle.gcal.Event],
    dry_run: bool = True,
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
                gregle.gcal.cal.post_delete(api, calendar, eid, dry_run=dry_run)
            except Exception as exc:
                gregle.log.error("Failed to delete event %s", event, exc_info=exc)
        else:
            gregle.log.error("Event %s has no ID", event)


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Google Calendar with LU Timetable")

    parser.add_argument("--force", action="store_true", help="Force update GCals events from LU")
    parser.add_argument("--dry-run", action="store_true", help="Do not make any changes to Google Calendar")
    parser.add_argument("--no-cache", dest="cache", action="store_false", help="Do not use cached data")
    parser.add_argument("-v", "--verbose", dest="log_level", action="count", default=0, help="Increase verbosity")

    return parser.parse_args()


def main() -> None:
    ns = cli()
    log_config(ns.log_level)
    try:
        local, date_range = events_local(ns.cache)
        with gregle.gcal.service.calendar() as api:
            calendar = gregle.gcal.cal.get_calendar(api, "Timetable")
            remote = events_remote(api, calendar, date_range)
            if ns.force:
                for event in remote:
                    if eid := event.id():
                        pp(event)
                        gregle.gcal.cal.post_delete(api, calendar, eid, dry_run=ns.dry_run)
                for event in local:
                    pp(event)
                    gregle.gcal.cal.post_create(api, calendar, gregle.gcal.Event.from_event(event), dry_run=ns.dry_run)
            else:
                for change in gregle.lu.diff(list(gcal_to_lu(api, calendar, remote, ns.dry_run)), local):
                    pp(change)
                    gregle.gcal.cal.process_diff(api, calendar, change, dry_run=ns.dry_run)
    except Exception as e:
        gregle.log.fatal("Unhandled exception", exc_info=e)
        raise


if __name__ == "__main__":
    main()
