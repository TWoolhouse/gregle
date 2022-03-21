from gcal import Google
from extract import Extractor
import timetable

def main():
	lessons = timetable.convet_raw(Extractor())
	with Google(lessons) as google:
		print("Done!")

if __name__ == "__main__":
	main()
