import datetime
import functools
import pickle
from collections.abc import Callable
from pathlib import Path


class FuncCache[R]:
    def __init__(self, func: Callable[[], R], filepath: Path, lifetime: datetime.timedelta) -> None:
        self.func = func
        self.filepath = filepath
        self.lifetime = lifetime

    def read(self) -> R:
        if not stale(self.filepath, self.lifetime):
            return self.read_stale()
        raise FileNotFoundError(f"{self.filepath} is stale")

    def read_stale(self) -> R:
        with self.filepath.open("rb") as f:
            return pickle.load(f)

    def write(self) -> R:
        r = self.func()
        with self.filepath.open("wb") as f:
            pickle.dump(r, f)
        return r

    def rw(self) -> R:
        if stale(self.filepath, self.lifetime):
            return self.write()
        return self.read_stale()

    def __call__(self) -> R:
        return self.rw()


def file[R](filepath: Path, lifetime: datetime.timedelta) -> Callable[[Callable[[], R]], FuncCache[R]]:
    def file_decorator(func: Callable[[], R]) -> FuncCache[R]:
        return FuncCache(func, filepath, lifetime)

    return file_decorator


def stale(filepath: Path, lifetime: datetime.timedelta) -> bool:
    return (
        not filepath.exists()
        or (datetime.datetime.now() - datetime.datetime.fromtimestamp(filepath.stat().st_mtime)) >= lifetime
    )
