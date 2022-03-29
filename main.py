from gcal import Google
from extract import Extractor
import timetable
from log import log

def main():
	log.info(">---------- Begin ----------<")
	lessons = timetable.convet_raw(Extractor())
	with Google(lessons) as google:
		log.info(">---------- Done! ----------<")

if __name__ == "__main__":
	main()
