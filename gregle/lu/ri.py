import base64
import datetime
import re
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Self

import selenium
import selenium.common
import selenium.webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from .. import path as PATH
from .. import tz
from ..log import log
from .event import EventGroup, EventRaw, GroupID

type WebDriver = selenium.webdriver.Chrome

RE_WEEK = re.compile(r"Sem\s*\d+\s*-\s*Wk\s*(\d+)\s*\(starting\s*(\d{2}-\w{3}-\d{4})\)", re.I)


type Week = tuple[WebElement, int, datetime.date]


@dataclass
class WeekSelector:
    selector: Select
    weeks: list[Week]

    @property
    def current(self) -> Week:
        chosen = self.selector.first_selected_option
        for week in self.weeks:
            if week[0] == chosen:
                return week
        raise ValueError("The currently selected item is not a valid week")

    @classmethod
    def from_driver(cls, driver: WebDriver) -> Self:
        selector = Select(driver.find_element(By.ID, "P2_MY_PERIOD"))

        weeks = []
        for item in selector.options:
            name = (item.get_attribute("innerText") or "").lower()
            if (m := RE_WEEK.match(name)) is None:
                continue
            date = datetime.datetime.strptime(m[2], "%d-%b-%Y").date()
            weeks.append((item, int(m[1]), date))
        return cls(selector, weeks)

    def set(self, week: Week) -> None:
        self.selector._set_selected(week[0])  # noqa: SLF001


def events_from_week(driver: WebDriver, week: datetime.date) -> set[EventRaw]:
    week_start = datetime.datetime.combine(week, datetime.time(hour=9), tz.DEFAULT)
    weeks = WeekSelector.from_driver(driver)
    week_id_map = {wk[1]: wk[2] for wk in weeks.weeks}

    log.info("Parsing LU Week: %s", week_start)

    events: set[EventRaw] = set()

    table = driver.find_element(By.ID, "timetable_details")
    weekday = -1
    for row in table.find_elements(By.CLASS_NAME, "tt_info_row"):
        nodes = list(row.find_elements(By.CSS_SELECTOR, ":scope > td"))

        if "weekday_col" not in (nodes[0].get_attribute("class") or ""):
            continue
        if "on demand" in (nodes[0].get_attribute("innerHTML") or "").lower():
            continue

        weekday += 1
        loc = -1  # Offset -1 as we pre increment
        for node in nodes[1:]:
            loc += 1
            if "new_row_tt_info_cell" not in (node.get_attribute("class") or ""):
                continue
            dt = datetime.timedelta(days=weekday, hours=loc / 2)
            event, repeats = event_from_node(node, week_start + dt)
            loc += (event.duration.total_seconds() / 60 / 60) * 2 - 1
            events.add(event)
            for repeat_wk in repeats:
                events.add(
                    event.with_date(
                        (datetime.datetime.combine(week_id_map[repeat_wk], datetime.time(), tz.DEFAULT) + dt).date()
                    )
                )

    log.info("Found %d LU events", len(events))

    return events


def event_from_node(node: WebElement, start: datetime.datetime) -> tuple[EventRaw, list[int]]:
    def get_content_of(class_name: str) -> str | None:
        try:
            return node.find_element(By.CLASS_NAME, class_name).get_attribute("innerText")
        except selenium.common.NoSuchElementException as exc:
            log.exception("Failed to find element '.%s' on node %s", class_name, node, stack_info=True)
            return None

    def remove_ellipsis(string: str) -> str:
        if string.endswith("..."):
            string = string[: -len("...")]
        return string

    def split(string: str) -> tuple[str, ...]:
        s = {ss for s in remove_ellipsis(string).split(",") if (ss := s.strip())}
        return tuple(sorted(s - {"..."}))

    duration = int(node.get_attribute("colspan") or "") // 2  # hours
    module_codes = split(get_content_of("tt_module_id_row") or "")
    module_name = remove_ellipsis(get_content_of("tt_module_name_row") or "")
    lecturers = split(get_content_of("tt_lect_row") or "")
    rooms = split(get_content_of("tt_room_row") or "UNKNOWN")
    content_type = get_content_of("tt_modtype_row")

    return EventRaw(
        module_codes,
        module_name or "",
        rooms,
        lecturers,
        content_type or "",
        start,
        datetime.timedelta(hours=duration),
    ), extract_repeated_weeks((get_content_of("tt_weeks_row") or "").lower())


def extract_repeated_weeks(weeks: str) -> list[int]:
    PREFIX = "weeks:"
    weeks = weeks.lstrip(PREFIX).lstrip()
    ranges = weeks.split(":", maxsplit=1)[1].split(",")

    out = []
    for rng in ranges:
        rng = rng.strip()
        if "-" in rng:
            lhs, rhs = (int(s.strip()) for s in rng.split("-"))
            out.extend(range(lhs, rhs + 1))
        else:
            out.append(int(rng))
    return out


def driver_build() -> WebDriver:
    driver = selenium.webdriver.Chrome()
    driver.implicitly_wait(5)
    return driver


def navigate_to_timetable(driver: WebDriver, /, headless: bool) -> WebDriver:
    URL = "https://lucas.lboro.ac.uk/its_apx/f?p=student_timetable"
    log.info("Navigating to live timetable: %s", URL)
    driver.get(URL)
    if headless:
        _navigate_to_timetable_auto(driver)
    else:
        EXPECTED = "https://lucas.lboro.ac.uk/its_apx/f"
        WebDriverWait(driver, 120, poll_frequency=1).until(
            EC.all_of(
                EC.url_changes(URL),  # We have redirected
                EC.url_contains(EXPECTED),  # We are probably on the right page
                EC.presence_of_element_located(  # We have loaded the timetable
                    (By.ID, "timetable"),
                ),
            )
        )
    return driver


def _navigate_to_timetable_auto(driver: WebDriver):
    # TODO: Automagically sign-in?
    raise NotImplementedError()


def navigate_iter_weeks(driver: WebDriver) -> Iterator[tuple[WebDriver, Week]]:
    wksel = WeekSelector.from_driver(driver)
    for week in wksel.weeks:
        wksel.set(week)
        time.sleep(1)
        yield (driver, week)


def navigate_to_src(driver: WebDriver, src: str) -> WebDriver:
    html = base64.b64encode(src.encode("utf-8")).decode()
    driver.get("data:text/html;base64," + html)
    return driver


def iter_weeks_cache_load(driver: WebDriver, cache: Path) -> Iterator[tuple[WebDriver, datetime.date]]:
    log.info("Parsing weeks from cache")
    for filename in cache.glob("*.html"):
        yield (navigate_to_src(driver, filename.read_text()), datetime.date.fromisoformat(filename.stem))


def iter_weeks_cache_store(driver: WebDriver, cache: Path) -> Iterator[tuple[WebDriver, datetime.date]]:
    navigate_to_timetable(driver, headless=False)
    log.info("Saving weeks to cache")
    for d, wk in navigate_iter_weeks(driver):
        (cache / f"{wk[2].isoformat()}.html").write_text(d.page_source)
        yield (d, wk[2])


def iter_weeks(driver: WebDriver, cache: Path) -> Iterator[tuple[WebDriver, datetime.date]]:
    f_cache_info = cache / "meta.cache"
    if (
        f_cache_info.exists()
        and (time.time() - f_cache_info.stat().st_mtime) < datetime.timedelta(minutes=30).total_seconds()
    ):
        return iter_weeks_cache_load(driver, cache)

    f_cache_info.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    return iter_weeks_cache_store(driver, cache)


def group_events(events: Iterable[EventRaw]) -> list[EventGroup]:
    table: dict[GroupID, set[EventRaw]] = defaultdict(set)

    for event in events:
        table[event.group()].add(event)

    groups = []
    for events in table.values():
        events = sorted(events, key=lambda event: event.start)
        groups.append(EventGroup(None, events[0], [event.start.date() for event in events[1:]]))

    return groups


def events_raw() -> tuple[set[EventRaw], tuple[datetime.date, datetime.date]]:
    driver = driver_build()
    events: set[EventRaw] = set()
    weeks: list[datetime.date] = []
    for d, wk in iter_weeks(driver, PATH.CACHE):
        weeks.append(wk)
        events.update(events_from_week(d, wk))

    return events, (
        min(weeks),
        (datetime.datetime.combine(max(weeks), datetime.time(9)) + datetime.timedelta(weeks=1)).date(),
    )


def events() -> tuple[list[EventGroup], tuple[datetime.date, datetime.date]]:
    e, ds = events_raw()
    es = group_events(e)
    log.info("Total Events: %d", len(es))
    return es, ds
