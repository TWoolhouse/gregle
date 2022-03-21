L = "Loughborough"
LU = "Loughborough University"
LE113TU = f"{LU}, Margaret Keay Road, {L} LE11 3TU"
LE113TP = f"University Road, {L} LE11 3TP"

BUILDING = {
	"CC": f"James France, {LE113TU}",
	"N": f"Haslegrave Building, {LE113TP}",
	"U": f"Brockington Building, {LE113TU}",
	"SMB": f"Stewart Mason Building, {LE113TU}",
	"MST": "Microsoft Teams"
}
BUILDING_CODES = tuple(sorted(BUILDING.keys(), key=len, reverse=True))

def building(code: str) -> str:
	for b in BUILDING_CODES:
		if code.startswith(b):
			return BUILDING[b]
	raise KeyError("Building is not Mapped!")

def address(code: str) -> str:
	return f"{code}, {building(code)}"
