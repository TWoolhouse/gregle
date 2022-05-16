from sys import exc_info
from gcal import Google
from extract import Extractor
import timetable
from log import log

def main():
	try:
		log.info(">---------- Begin ----------<")
		lessons = timetable.convet_raw(Extractor())
		with Google(lessons) as google:	pass
	except Exception as e:
		log.error("Unknown Runtime Error", exc_info=e)
	finally:
		log.info(">---------- Done! ----------<")

if __name__ == "__main__":
	main()
