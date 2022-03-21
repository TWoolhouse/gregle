import collections
from pathlib import Path
from typing import Iterator, Literal
from bs4 import BeautifulSoup, Tag
from requests_html import HTMLSession
from datetime import datetime, date
import json

RES = Path(__file__).parent / "res"
CACHE_TIME = RES / "cache.txt"
CACHE = RES / "timetable.html"


WEEK_DAYS = (
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
)

class Extractor:
	def __init__(self, query: bool=True) -> None:
		if query and self.cache_expiry(CACHE_TIME):
			self.execute_request(CACHE)

		with open(CACHE, "rb") as file:
			self.soup = BeautifulSoup(file, "html.parser")
		print(">----- Extracting Calendar -----<")
		self.current_week: date = date(1, 1, 1)
		self.lectures = self._find_lectures()
		self.weeks = self._find_weeks()

	def _find_weeks(self) -> dict[int, list[date]]:
		weeks = (self.soup.find("select", "selectlist", id="P2_MY_PERIOD"))
		sems: dict[int, list[date]] = collections.defaultdict(list)
		for week in weeks.children:
			try:
				int(week["value"])
			except (ValueError, TypeError):	continue
			wk: str = week.string.strip().upper()
			if wk.startswith("SEM"):
				sem = int(wk.split(" ", 2)[1].strip())
				sar = sems[sem]
				date_ = wk[wk.rfind("(") + 1:-1].split(" ", 1)[1]
				out = datetime.strptime(date_, "%d-%b-%Y").date()
				sar.append(out)
				if "selected" in week.attrs and week["selected"] == "selected":
					self.current_week = out
		for sem in sems.values():
			sem.sort()
		print("Current Week:", self.current_week.strftime("%d/%m/%Y"))
		return sems

	def _find_lectures(self):
		table: Tag = self.soup.find("table", id="timetable_details")
		lectures = {tag: m for tag in table.find_all("div", "tt_content") if (m := self.lesson(tag))}
		for dayrow in table.find_all("tr", "tt_info_row"):
			children: Iterator[Tag] = iter(dayrow.children)
			if (day := next(children).string.strip().title()) not in WEEK_DAYS:
				continue
			time = 9
			for point in children:
				try:
					if "colspan" not in point.attrs:
						time += 0.5
						continue
				except AttributeError:
					continue
				if lecture := lectures.get(next(iter(point.children)), None):
					length = int(point["colspan"]) // 2
					lecture["day"] = day
					lecture["time"] = str(int(time))
					lecture["length"] = str(length)
					time += length
		print("Found Lessons:", len(lectures))
		return list(lectures.values())

	FIELDS = {
		"module": "module_id",
		"name": "module_name",
		"lecturer": "lect",
		"room": "room",
		"type": "modtype",
		"weeks": "weeks",
	}
	def lesson(self, lesson: Tag) -> dict[str, str] | Literal[False]:
		try:
			return {name: lesson.find(class_=f"tt_{cls}_row").string for name, cls in self.FIELDS.items()}
		except AttributeError:
			return False

	TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
	def cache_expiry(self, path: Path) -> bool:
		try:
			with open(path, "r") as file:
				dt = datetime.now() - datetime.strptime(file.readline().strip(), self.TIME_FORMAT)
		except FileNotFoundError:	return True
		return dt.total_seconds() > 60

	def cache_time(self, path: Path):
		with open(path, "w") as file:
			file.write(datetime.now().strftime(self.TIME_FORMAT))

	def execute_request(self, path: Path):
		print(">----- Loughborough Web Calendar -----<")
		print("Requesting Timetable")
		URL = "https://lucas.lboro.ac.uk/its_apx/f?p=student_timetable"
		USER_AGENT = {
			"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
		}

		def read_form_data(form) -> tuple[str, dict[str, str]]:
			fields: dict[str, str] = {}
			for field in form.find("input"):
				if (v := field.attrs.get("value", None)) and "name" in field.attrs:
					fields[field.attrs["name"]] = v
			return form.attrs.get("action", None), fields

		session = HTMLSession()

		# TIMETABLE PAGE
		r = session.get(
			URL,
			headers=USER_AGENT,
			allow_redirects=True,
		)

		form = r.html.find("section#main-content form", first=True)

		with open(RES / "creds.json") as file:
			credentials = json.load(file)

		_, fields = read_form_data(form)
		fields[form.find("#username", first=True).attrs["name"]] = credentials["username"]
		fields[form.find("#password", first=True).attrs["name"]] = credentials["password"]

		print("Requesting Sign In")

		# SIGN-IN PAGE
		r = session.post(
			r.url,
			data=fields,
			headers=USER_AGENT,
			allow_redirects=True,
		)

		form = r.html.find("form", first=True)
		url, fields = read_form_data(form)

		print("Requesting Content")
		# Content Page
		r = session.post(
			url,
			data=fields,
			headers=USER_AGENT,
			allow_redirects=True,
		)

		r.html.render(sleep=0.25, reload=True)
		print("Calendar Cache Downloading")
		with open(path, "wb") as file:
			file.writelines(r.iter_content())
		self.cache_time(CACHE_TIME)
