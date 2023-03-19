import logging
import os
import sys
from pathlib import Path

PATH = Path(sys.argv[0]).resolve().parent.absolute()



formatter = logging.Formatter(
	"[{levelname} {asctime}] {module}.{funcName} -> {message}",
	datefmt="%Y/%m/%d %H:%M:%S", style="{"
)

class Logger(logging.Logger):

	def _clog(self, func, msg, *args, **kwargs):
		if er := kwargs.pop("exc_info", None):
			er = (er, er, er.__traceback__)
		return func(msg, *args, stacklevel=3, exc_info=er, **kwargs)

	def debug(self, msg, *args, **kwargs):
		return self._clog(super().debug, msg, *args, **kwargs)
	def info(self, msg, *args, **kwargs):
		return self._clog(super().info, msg, *args, **kwargs)
	def warning(self, msg, *args, **kwargs):
		return self._clog(super().warning, msg, *args, **kwargs)
	def error(self, msg, *args, **kwargs):
		return self._clog(super().error, msg, *args, **kwargs)
	def critical(self, msg, *args, **kwargs):
		return self._clog(super().critical, msg, *args, **kwargs)

class Handle(logging.FileHandler):

	def __init__(self, file: str, mode: str):
		folder_name = PATH / "log"
		if not folder_name.exists():
			os.makedirs(folder_name)
		file_names = [folder_name / f"{file}{suffix}" for suffix in (".log", ".trace.log")]
		for fname in file_names:
			with open(fname, "w") as f:	pass
		self._trace_handle = logging.FileHandler(str(file_names[1]), mode, "utf-8")
		self._trace_handle.setLevel(logging.NOTSET)
		self._trace_handle.setFormatter(formatter)
		super().__init__(str(file_names[0]), mode, "utf-8")

	def format(self, record):
		err = record.exc_info
		record.exc_info = None
		msg = super().format(record)
		if err:
			record.exc_info = err
			self._trace_handle.emit(record)
		print(msg)
		return msg

def create(name: str, fmt: str=None) -> Logger:
	logging.Logger.manager.setLoggerClass(Logger)
	logger = logging.getLogger(name)
	logging.Logger.manager.setLoggerClass(logging.Logger)
	logger.setLevel(logging.DEBUG)
	handle = Handle(name, "a")
	if fmt:
		fmtr = logging.Formatter(fmt, datefmt="%Y/%m/%d %H:%M:%S", style="{")
		handle.setFormatter(fmtr)
		handle._trace_handle.setFormatter(fmtr)
	else:
		handle.setFormatter(formatter)
	logger.addHandler(handle)
	return logger

log = create("calendar")
