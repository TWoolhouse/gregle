import datetime
import logging.config
from pprint import pp

import gregle


def log_config() -> None:
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
                    "filename": "gregle.log",
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


def main() -> None:
    log_config()
    try:
        local, date_range = events_local()
        with gregle.gcal.service.calendar() as api:
            calendar = gregle.gcal.cal.get_calendar(api, "Timetable")
            remote = events_remote(api, calendar, date_range)
            for change in gregle.lu.diff([gregle.lu.Events.from_event(e) for e in remote], local):
                pp(change)
                gregle.gcal.cal.process_diff(api, calendar, change)
    except Exception as e:
        gregle.log.fatal("Unhandled exception", exc_info=e)
        raise


main()
