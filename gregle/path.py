from pathlib import Path


def new(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


CODE = Path(__file__).parent
ROOT = CODE.parent
RES = new(ROOT / "res")
CACHE = new(ROOT / "cache")
