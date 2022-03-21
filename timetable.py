import enum
import datetime
from dataclasses import dataclass
from addresses import address
from extract import Extractor

@dataclass
class Module:
	code: str
	name: str
	professors: list[str]

@dataclass
class Room:
	code: str
	@property
	def address(self) -> str:
		return address(self.code)

@enum.unique
class LessonType(enum.IntEnum):
	Lecture = 1
	Workshop = 2
	Laboratory = 3
	Tutorial = 4
	Drop_In_Session = 5

@dataclass
class Time:
	day: int
	start: datetime.time
	duration: datetime.timedelta
	@property
	def end(self) -> datetime.time:
		return (datetime.datetime.combine(datetime.date.today(), self.start)+self.duration).time()

	def __hash__(self) -> int:
		return (self.day, self.start, self.duration).__hash__()

@dataclass
class Weeks:
	dates: list[datetime.date]
	@property
	def begin(self) -> datetime.date:
		return self.dates[0]
	@property
	def end(self) -> datetime.date:
		return self.dates[-1]
	def excludes(self) -> list[datetime.date]:
		WEEK = datetime.timedelta(weeks=1)
		exclusions = []
		last = self.begin
		for week in self.dates:
			while week - last > WEEK:
				last += WEEK
				exclusions.append(last)
			last = week
		return exclusions

@dataclass
class Lesson:
	module: Module
	room: Room
	time: Time
	weeks: Weeks
	type: LessonType

	def fuzzy(self) -> tuple[str, Time]:
		return (self.module.code, self.time)

DAYS = [
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday"
]
def convet_raw(extract: Extractor) -> list[Lesson]:
	lessons = []
	for lecture in extract.lectures:
		weeks: list[datetime.date] = []
		wks = lecture["weeks"]
		_, sem, groups = wks.split(":", 2)
		sem = int(sem.lstrip().split(" ", 1)[1].strip())
		for grp in groups.split(","):
			if "-" in grp:
				for wk in range((dr := tuple(map(lambda i: int(i.strip()), grp.split("-"))))[0], dr[1] + 1):
					weeks.append(extract.weeks[sem][wk - 1])
			else:
				weeks.append(extract.weeks[sem][int(grp) - 1])
		weeks.sort()

		day_delta = datetime.timedelta(days=DAYS.index(lecture["day"].lower()))
		lessons.append(Lesson(
			Module(lecture["module"], lecture["name"], list(map(lambda x: x.strip(), (prof[:-3] if (prof := lecture["lecturer"]).endswith("...") else prof).split(",")))),
			Room(Room(lecture["room"]).address.split(",")[0].strip()),
			Time(day_delta.days, datetime.time(int(lecture["time"])), datetime.timedelta(hours=int(lecture["length"]))),
			Weeks([wk + day_delta for wk in weeks]),
			LessonType[lecture["type"].split("/")[0].strip().title().replace(" ", "_")],
		))
	return lessons
