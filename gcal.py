import datetime
from zoneinfo import ZoneInfo
from typing import Any, Generator, Iterable

import timetable
from gcal_api import API, calendar_service
import ftime
from log import log

DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DAY_DELTA = datetime.timedelta(days=1)
class Google:

	def __init__(self, lessons: Iterable[timetable.Lesson]) -> None:
		self.lessons = lessons
		date = datetime.datetime.now()
		# date = datetime.datetime(2021, 11, 2, 0, 0, 0)
		self.week_start = date - datetime.timedelta(days=date.weekday())
		self.week_end = self.week_start + datetime.timedelta(days=7)

	def __str__(self) -> str:
		return "Google Calendar"

	def __enter__(self):

		with calendar_service() as self.api:
			log.info(">----- Google API -----<")
			self.calendar = self.obtain_calendar()
			active_events = {event[1].fuzzy(): [*event, False] for event in self.generate_events()}
			for lesson in self.lessons:
				if not (event := active_events.get(lesson.fuzzy())):
					self.upload(lesson)
					continue
				elif lesson != event[1]:
					self.update(event[0], lesson, reason="Updates")
				event[2] = True
			for eid, lesson, f in active_events.values():
				if not f:
					lesson.weeks.dates.remove(datetime.datetime.combine(self.week_start.date() + datetime.timedelta(days=lesson.time.day), lesson.time.start).date())
					self.update(eid, lesson, "Expired")
		return self

	def __exit__(self, *args):
		return

	def obtain_calendar(self) -> str:
		NAME = "Timetable"
		page_token: str | None = None
		while True:
			log.info("Request: Calendars")
			res: dict = self.api.calendarList().list(pageToken=page_token).execute()
			for cal in res["items"]:
				if cal["summary"].lower() == NAME.lower():
					return cal["id"]
			if (page_token := res.get("nextPageToken")) is None:
				break
		raise ValueError(f"No Calendar {NAME}")

	def generate_events(self) -> Generator[tuple[str, timetable.Lesson], None, None]:
		WEEK = datetime.timedelta(weeks=1)
		page_token: str | None = None
		while True:
			log.info("Request: Events")
			res: dict = self.api.events().list(
				calendarId=self.calendar,
				timeMin=ftime.fmt(self.week_start - WEEK),
				timeMax=ftime.fmt(self.week_end + WEEK),
				pageToken=page_token
			).execute()
			for event in res["items"]:
				yield (event["id"], self.deventify(event))
			if (page_token := res.get("nextPageToken")) is None:
				break

	def eventify(self, lesson: timetable.Lesson) -> dict[str, Any]:
		# "id", "summary", "description", "location", "start", "end", "recurrence"
		return {
			"summary": f"{lesson.module.name} - {lesson.module.code}",
			"description": f"{lesson.module.code} - {lesson.type.name.replace('_', ' ')}\n{', '.join(lesson.module.professors)}",
			"location": lesson.room.address,
			"start": {
				"dateTime": ftime.fmt(datetime.datetime.combine(lesson.weeks.begin, lesson.time.start, ftime.TZ)),
				"timeZone": str(ftime.TZ)
			},
			"end": {
				"dateTime": ftime.fmt(datetime.datetime.combine(lesson.weeks.begin, lesson.time.end, ftime.TZ)),
				"timeZone": str(ftime.TZ)
			},
			"recurrence": [i for i in [
				f"RRULE:FREQ=WEEKLY;BYDAY={DAYS[lesson.time.day]};UNTIL={(lesson.weeks.end + DAY_DELTA).strftime(ftime.ISO_SHORT)}Z",
				("EXDATE:" + ','.join(datetime.datetime.combine(exc, lesson.time.start).strftime(ftime.ISO_SHORT) for exc in lesson.weeks.excludes())) if lesson.weeks.excludes() else ""
			] if i]
		}

	def deventify(self, event: dict[str, Any]) -> timetable.Lesson:
		name, code = event["summary"].strip().rsplit("-", 1)
		ltype, profs = event["description"].split("-", 1)[1].strip().split("\n", 1)
		location = event["location"].split(",", 1)[0].strip()

		start = ftime.read(event["start"]["dateTime"], tz=False)
		end = ftime.read(event["end"]["dateTime"], tz=False)
		week_end: datetime.date
		exdate: list[datetime.date] = []
		for rec in event["recurrence"]:
			if rec.startswith("EXDATE"):
				for time in rec[rec.find(":")+1:].split(","):
					exdate.append(ftime.read(time, ftime.ISO_SHORT, tz=False).date())
			elif rec.startswith("RRULE"):
				for field in rec[len("RRULE:"):].split(";"):
					attr, val = field.split("=")
					if attr.upper() == "UNTIL":
						week_end = ftime.read(val, ftime.ISO_SHORT, tz=False).date()
						break

		WEEK = datetime.timedelta(weeks=1)
		weeks: list[datetime.date] = []
		last = start.date()
		while last <= week_end:
			if last not in exdate:
				weeks.append(last)
			last += WEEK

		# TODO: Fill out Fields
		return timetable.Lesson(
			timetable.Module(code.lstrip(), name.rstrip(), list(map(str.strip, profs.split(",")))),
			timetable.Room(location),
			timetable.Time(start.weekday(), start.time(), end - start),
			timetable.Weeks(weeks),
			timetable.LessonType[ltype.replace(" ", "_")],
		)

	def upload(self, lesson: timetable.Lesson) -> str:
		try:
			log.info(f"Uploading Lesson: {lesson.module.code} {lesson.module.name} {DAYS[lesson.time.day]} {ftime.fmt(datetime.datetime.combine(lesson.weeks.begin, lesson.time.start, ftime.TZ))}")
			return self.api.events().insert(calendarId=self.calendar, body=self.eventify(lesson)).execute()["id"]
		except Exception as e:
			log.error(f"Uploading\n\tLesson: {lesson}\n\tEvent: {self.eventify(lesson)}", exc_info=e)
			raise

	def update(self, eid: str, lesson: timetable.Lesson, reason="Updates") -> str:
		if not lesson.weeks.dates:
			log.warning(f"Removing Dead Event: {eid}, {lesson.module.code} {lesson.module.name} {DAYS[lesson.time.day]}")
			return eid
		try:
			log.info(f"Patching<{reason}> Lesson: {lesson.module.code} {lesson.module.name} {DAYS[lesson.time.day]} {ftime.fmt(datetime.datetime.combine(lesson.weeks.begin, lesson.time.start, ftime.TZ))}")
			return self.api.events().update(calendarId=self.calendar, eventId=eid, body=self.eventify(lesson)).execute()["id"]
		except Exception as e:
			log.error(f"Patching <{reason}>\n\tLesson: {lesson}\n\tEvent: {self.eventify(lesson)}", exc_info=e)
			raise
