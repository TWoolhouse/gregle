import datetime
import pickle
from collections.abc import Callable
from pathlib import Path


class FuncCache[**P, R]:
    def __init__(self, func: Callable[P, R], filepath: Path, lifetime: datetime.timedelta) -> None:
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

    def write(self, *args: P.args, **kwargs: P.kwargs) -> R:
        r = self.func(*args, **kwargs)
        with self.filepath.open("wb") as f:
            pickle.dump(r, f)
        return r

    def rw(self, *args: P.args, **kwargs: P.kwargs) -> R:
        if stale(self.filepath, self.lifetime):
            return self.write(*args, **kwargs)
        return self.read_stale()

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self.rw(*args, **kwargs)


def file[**P, R](filepath: Path, lifetime: datetime.timedelta) -> Callable[[Callable[P, R]], FuncCache[P, R]]:
    def file_decorator(func: Callable[P, R]) -> FuncCache[P, R]:
        return FuncCache(func, filepath, lifetime)

    return file_decorator


def stale(filepath: Path, lifetime: datetime.timedelta) -> bool:
    return (
        not filepath.exists()
        or (datetime.datetime.now() - datetime.datetime.fromtimestamp(filepath.stat().st_mtime)) >= lifetime
    )
