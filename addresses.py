BUILDING = {
	"EHB": "EHB, Margaret Keay Rd, Loughborough LE11 3TU",
	"LDS": "Loughborough Design School, Loughborough University, Loughborough LE11 3TU",
	"MHL": "Martin Hall, Epinal Way, Loughborough LE11 3TS",
	"MST": "Microsoft Teams",
	"SCH": "Schofield Building, University Rd, Loughborough LE11 3TU",
	"SMB": "Stewart Mason Building, Margaret Keay Rd, Loughborough LE11 3TU",
	"WAV": "Wavy Top, Loughborough LE11 3TU",
	"WPT": "West Park Teaching Hub, 2 Oakwood Dr, Loughborough LE11 3QF",
	"WPL": "STEMLab, University Rd, Loughborough LE11 3TL",
	"DAV": "Loughborough University Physics Department, Epinal Way, Loughborough LE11 3TU",
	"CC": "James France, Margaret Keay Rd, Loughborough LE11 3TW",
	"TW": "Wolfson School of Mechanical, Electrical and Manufacturing Engineering, Loughborough University, Wolfson Building, Ashby Rd, Loughborough LE11 3TU",
	"N": "Haslegrave Building, University Rd, Loughborough LE11 3TP",
	"U": "Brockington Building, Loughborough University, Margaret Keay Rd, Loughborough LE11 3TU",
	"T": "Wolfson School of Mechanical, Electrical and Manufacturing Engineering, Loughborough University, Wolfson Building, Ashby Rd, Loughborough LE11 3TU",
}

BUILDING_CODES = tuple(sorted(BUILDING.keys(), key=len, reverse=True))

def building(code: str) -> str:
	for b in BUILDING_CODES:
		if code.startswith(b):
			return BUILDING[b]
	raise KeyError("Building is not Mapped!")

def address(code: str) -> str:
	return f"{code}, {building(code)}"
