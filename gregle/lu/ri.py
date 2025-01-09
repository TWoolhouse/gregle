import base64
import contextlib
import datetime
import re
import time
from collections.abc import Generator, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import selenium
import selenium.common
import selenium.webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from .. import cache, tz
from .. import path as PATH
from ..log import log
from .event import EventInstance, EventSchedule, GroupID

type WebDriver = selenium.webdriver.Chrome

RE_WEEK = re.compile(r"Sem\s*(\d+)\s*-\s*Wk\s*(\d+)\s*\(starting\s*(\d{2}-\w{3}-\d{4})\)", re.I)
"""Regex to match a week name in the timetable's selector dropdown

- Semester ID
- Week ID
- Week Start Date"""

type SemWk = tuple[int, int]
"""Semester and Week ID"""
type SemWks = set[SemWk]
"""Set of weeks that an event repeats on"""


@dataclass
class Week:
    element: WebElement
    semester: int
    wk: int
    date: datetime.date


type WeekMap = dict[SemWk, Week]


@dataclass
class PageSelector:
    selector: Select
    weeks: list[Week]
    semesters: dict[int, WebElement]

    @property
    def current(self) -> Week:
        chosen = self.selector.first_selected_option
        for week in self.weeks:
            if week.element == chosen:
                return week
        raise ValueError("The currently selected item is not a valid week")

    @classmethod
    def from_driver(cls, driver: WebDriver) -> Self:
        selector = Select(driver.find_element(By.ID, "P2_MY_PERIOD"))

        weeks: list[Week] = []
        semesters: dict[int, WebElement] = {}
        for item in selector.options:
            name = (item.get_attribute("innerText") or "").lower()
            if (m := RE_WEEK.match(name)) is not None:
                date = datetime.datetime.strptime(m[3], "%d-%b-%Y").date()  # noqa: DTZ007
                weeks.append(Week(item, int(m[1]), int(m[2]), date))
            elif name.startswith("semester"):
                semesters[int(name.split()[-1])] = item
        return cls(selector, weeks, semesters)

    def set(self, opt: Week | WebElement) -> None:
        self.selector._set_selected(opt if isinstance(opt, WebElement) else opt.element)  # noqa: SLF001

    def map(self) -> WeekMap:
        return {(week.semester, week.wk): week for week in self.weeks}


def fmt_element(node: WebElement) -> str:
    eid = node.get_attribute("id")
    if eid:
        eid = f"#{eid}"
    classes = ".".join((node.get_attribute("class") or "").split())
    if classes:
        classes = f".{classes}"
    return f"{node.tag_name}{eid}{classes}"


def extract_repeated_weeks(weeks: str) -> Iterator[SemWk]:
    """Extract the weeks that an event repeats on from the timetable."""
    PREFIX = "weeks:"
    weeks = weeks.lstrip(PREFIX).lstrip()
    for sem_data in weeks.split("sem"):
        sem_data = sem_data.strip()
        if not sem_data:
            continue
        sem_name, weeks = map(str.strip, sem_data.split(":"))
        sem = int(sem_name)
        for rng in weeks.split(","):
            rng = rng.strip()
            if "-" in rng:
                lhs, rhs = (int(s.strip()) for s in rng.split("-"))
                yield from ((sem, wk) for wk in range(lhs, rhs + 1))
            else:
                yield (sem, int(rng))


def event_from_node(node: WebElement, start: datetime.datetime, weeks: WeekMap) -> EventSchedule:
    """Extract an event from a node in the timetable.

    Args:
        node: The `WebElement` node representing the event.
        start: The `datetime` of the start of the event.
        weeks: A mapping of the weeks in the timetable to dates.

    Returns:
        An `EventSchedule` instance representing the event."""

    def get_content_of(class_name: str) -> str | None:
        try:
            return node.find_element(By.CLASS_NAME, class_name).get_attribute("innerText")
        except selenium.common.NoSuchElementException:
            log.exception("Failed to find element '.%s' on node %s", class_name, fmt_element(node), stack_info=True)
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
    rooms = split(get_content_of("tt_room_row") or "")
    content_type = get_content_of("tt_modtype_row")

    event = EventInstance(
        module_codes,
        module_name or "",
        rooms,
        lecturers,
        content_type or "",
        start.time(),
        datetime.timedelta(hours=duration),
    )
    instances = extract_repeated_weeks((get_content_of("tt_weeks_row") or "").lower())

    return EventSchedule(
        None, event, [weeks[semwk].date + datetime.timedelta(days=start.weekday()) for semwk in sorted(instances)]
    )


def events_from_weekday(
    nodes: list[WebElement],
    weekday: int,
    weeks: WeekMap,
) -> list[EventSchedule]:
    """Extract events from a weekday in the timetable.

    Args:
        nodes: The list of `WebElement` nodes representing columns in the timetable for a single weekday.
        weekday: The index of the weekday in the timetable. 0 is Monday.
        weeks: A mapping of the weeks in the timetable to dates.

    Returns:
        A list of `EventSchedule` instances representing the events on the weekday."""
    events: list[EventSchedule] = []

    loc = -1  # Offset -1 as we pre increment
    for node in nodes:
        loc += 1
        if "tt_info_cell" not in (node.get_attribute("class") or ""):
            continue
        dt = datetime.timedelta(days=weekday, hours=loc / 2)
        # 2000-01-03 is a Monday, so we can add the weekday to get the correct day
        day = datetime.datetime.combine(datetime.date(2000, 1, 3), datetime.time(hour=9), tz.DEFAULT)
        event = event_from_node(node, day + dt, weeks)
        loc += (event.instance.duration.total_seconds() / 60 / 60) * 2 - 1
        events.append(event)

    return events


def events_from_semester(driver: WebDriver, semester: int) -> list[EventSchedule]:
    """Extract events from the timetable the `driver` is currently on.

    Args:
        driver: The `WebDriver` pointing to the timetable.
        semester: The ID of the semester the timetable is for.

    Returns:
        A list of `EventSchedule` instances representing the events in the timetable."""
    pages = PageSelector.from_driver(driver)
    weeks = pages.map()

    log.info("Parsing LU Semester: %s", semester)

    events: list[EventSchedule] = []
    table = driver.find_element(By.ID, "timetable_details")
    weekday = -1
    with wait_timeout(driver, 0):
        weekdays = iter(table.find_elements(By.CLASS_NAME, "tt_info_row"))
        for row in weekdays:
            nodes = row.find_elements(By.CSS_SELECTOR, ":scope > td")

            if "weekday_col" not in (nodes[0].get_attribute("class") or ""):
                continue
            if "on demand" in (nodes[0].get_attribute("innerHTML") or "").lower():
                continue
            weekday += 1

            # The number of rows this weekday spans
            rows = int(nodes[0].get_attribute("rowspan") or "")

            events.extend(events_from_weekday(nodes[1:], weekday, weeks))
            for _ in range(rows - 1):
                events.extend(
                    events_from_weekday(
                        next(weekdays).find_elements(By.CSS_SELECTOR, ":scope > td"),
                        weekday,
                        weeks,
                    )
                )

    log.info("LU Semester found %d LU events over %d dates", len(events), sum(len(e.on_dates) for e in events))

    return events


def driver_build() -> WebDriver:
    """Build a new `WebDriver` instance."""
    opt = selenium.webdriver.ChromeOptions()
    opt.add_argument("--log-level=3")
    opt.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = selenium.webdriver.Chrome(options=opt)
    driver.implicitly_wait(1)
    return driver


@contextlib.contextmanager
def wait_timeout(driver: WebDriver, timeout: float = 0) -> Generator[None, None, None]:
    """Temporarily change the implicit wait timeout of a `WebDriver`.

    Restores the original timeout after the context manager exits."""
    old = driver.timeouts.implicit_wait
    try:
        driver.implicitly_wait(timeout)
        yield
    finally:
        driver.implicitly_wait(old)


def navigate_to_timetable(driver: WebDriver, *, headless: bool) -> WebDriver:
    """Navigate the `driver` to the live timetable page.

    The `driver` will wait for the user to sign in if `headless` is `False`."""
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


def navigate_to_src(driver: WebDriver, src: str) -> WebDriver:
    """Navigate the `driver` to a page with the given HTML `src`"""
    html = base64.b64encode(src.encode("utf-8")).decode()
    driver.get("data:text/html;base64," + html)
    return driver


def iter_semesters(driver: WebDriver, cache_dir: Path, use_cache: bool) -> Iterator[tuple[WebDriver, int]]:
    """Iterate over the semesters pages in the timetable

    Yields a tuple of the `WebDriver` pointing to the timetable and the semester ID.
    The timetable is cached in `cache_dir` and is stale after 1 hour.

    Returns:
        An iterator of tuples containing the `WebDriver` and the semester ID.
        The order is not guaranteed."""
    f_cache_info = cache_dir / "meta.cache"
    if not use_cache or cache.stale(f_cache_info, datetime.timedelta(hours=1)):
        log.info("Loading timetable from server...")
        navigate_to_timetable(driver, headless=False)
        cache_dir.mkdir(exist_ok=True, parents=True)
        pages = PageSelector.from_driver(driver)
        for semester, element in pages.semesters.items():
            pages.set(element)
            time.sleep(1)
            (cache_dir / f"{semester}.html").write_text(driver.page_source)
            yield (driver, semester)
        f_cache_info.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    else:
        log.info("Loading timetable from cache...")
        for filename in cache_dir.glob("*.html"):
            yield (navigate_to_src(driver, filename.read_text()), int(filename.stem))


def get_events(use_cache: bool) -> list[EventSchedule]:
    events: list[EventSchedule] = []
    for driver, semester in iter_semesters(driver_build(), PATH.CACHE / "semester", use_cache):
        events.extend(events_from_semester(driver, semester))
    return events


def dedupe_events(events: Iterable[EventSchedule]) -> list[EventSchedule]:
    """Deduplicate events by combining events that share the same `GroupID`

    Merges events that share the same `GroupID`, combining the dates they are on.

    Returns:
        A list of deduplicated events. The order of the events is not guaranteed.
        The ID of the events WILL NOT be preserved."""
    tbl: dict[GroupID, tuple[EventInstance, set[datetime.date]]] = {}

    for event in events:
        group = event.instance.group()
        if group in tbl:
            tbl[group][1].update(event.on_dates)
        else:
            tbl[group] = (event.instance, set(event.on_dates))

    return [EventSchedule(None, instance, sorted(dates)) for instance, dates in tbl.values()]


@cache.file(PATH.CACHE / "events.pkl", datetime.timedelta(minutes=60))
def events(html_cache: bool) -> list[EventSchedule]:
    es = get_events(html_cache)
    return dedupe_events(es)
