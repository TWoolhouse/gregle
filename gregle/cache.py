import datetime
import functools
import pickle
from collections.abc import Callable
from pathlib import Path


def file[R](filepath: Path, lifetime: datetime.timedelta) -> Callable[[Callable[[], R]], Callable[[], R]]:
    def file_decorator(func: Callable[[], R]) -> Callable[[], R]:
        @functools.wraps(func)
        def wrapper() -> R:
            if (
                filepath.exists()
                and (datetime.datetime.now() - datetime.datetime.fromtimestamp(filepath.stat().st_mtime)) < lifetime
            ):
                with filepath.open("rb") as f:
                    return pickle.load(f)

            r = func()
            with filepath.open("wb") as f:
                pickle.dump(r, f)
            return r

        return wrapper

    return file_decorator
