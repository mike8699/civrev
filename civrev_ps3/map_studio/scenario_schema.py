"""Scenario VARIATOR schema — the single source of truth for the settings UI.

Every DLC scenario entry (in dlcscenariodata{N}.xml) can carry a list of
``<VARIATOR><specs text="NAME" level="INT"/></VARIATOR>`` rules. The engine
parses them in FUN_0015c9b0 and stores each as a signed 16-bit short at
``scenario_struct + index*2``.

This module describes all 35 variators so the editor can render a correct,
typed control for each and validate combinations. Effects were established by
runtime probes on RPCS3 (see ../SCENARIO_VARIATORS.md); fields carry a
``status`` of ``"verified"`` (observed in-game) or ``"inferred"`` (from the
shipped-scenario prose). ``inferred`` fields are fully settable — the status
only changes how confidently the UI labels them.

STARTLOC encoding is ``value = row*256 + col`` in the map's display
coordinates (verified: display(17,6)=land matched probe 4358; the transpose is
ocean). See :func:`encode_startloc` / :func:`decode_startloc`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Value kinds ──────────────────────────────────────────────────────────────
# flag   : 0 / 1  → checkbox
# level  : small integer tier (0..max) → spinbox
# enum   : named choices → dropdown (options: list of (value, label))
# value  : free integer (bounded) → spinbox (gold, year, etc.)
# coord  : packed row*256+col tile → click-on-map (STARTLOC*)
# bitmask: raw integer bitmask → spinbox shown in advanced group (DISPLAYCARD)
KIND_FLAG = "flag"
KIND_LEVEL = "level"
KIND_ENUM = "enum"
KIND_VALUE = "value"
KIND_COORD = "coord"
KIND_BITMASK = "bitmask"

# ── Categories (UI grouping order) ───────────────────────────────────────────
CATEGORIES = [
    "Starting conditions",
    "Victory",
    "Barbarians & difficulty",
    "Economy & bonuses",
    "Map generation",
    "Advanced",
]

# Sentinel meaning "variator not present in this entry".
UNSET = None


@dataclass
class Variator:
    index: int
    name: str
    category: str
    kind: str
    label: str
    tooltip: str
    status: str = "inferred"          # "verified" | "inferred"
    default: int = 0                  # value used when the user enables it
    minimum: int = 0
    maximum: int = 9
    options: list = field(default_factory=list)   # for enum: [(value, label), ...]

    @property
    def verified(self) -> bool:
        return self.status == "verified"


# ── The 35 variators, in enum-index order ────────────────────────────────────
_V = [
    Variator(0, "BAGRESSIVE", "Barbarians & difficulty", KIND_LEVEL,
             "Barbarian aggressiveness",
             "How aggressively barbarians attack. Shipped values 0–2 "
             "(Global Warming/Enlightenment use 2 = 'raging' barbarians).",
             maximum=2),
    Variator(1, "BFECUNDITY", "Barbarians & difficulty", KIND_LEVEL,
             "Barbarian spawn rate",
             "How many barbarians spawn. 0 = 'few surviving', 2 = 'out in "
             "force'. Shipped values 0–2.",
             maximum=2),
    Variator(2, "BARBVSGOODY", "Barbarians & difficulty", KIND_LEVEL,
             "Hut barbarian ratio",
             "Ratio of barbarians to goody-huts in exploration huts; higher = "
             "more barbarians. Shipped values 1–2.",
             maximum=2),
    Variator(3, "RESOURCEDENSITY", "Map generation", KIND_LEVEL,
             "Resource density",
             "Abundance of map resources. Only affects RANDOM maps — a pre-"
             "baked scenario .map already has its resources fixed.",
             maximum=2),
    Variator(4, "TECHNOLOGYRATE", "Economy & bonuses", KIND_LEVEL,
             "Research speed",
             "Faster research. Verified: level 2 → 6 turns/tech vs the "
             "baseline 7.",
             status="verified", default=2, maximum=3),
    Variator(5, "UPGRADERATE", "Economy & bonuses", KIND_LEVEL,
             "Upgrade rate",
             "Unit upgrade cost/rate (exact effect not yet verified in-game).",
             maximum=3),
    Variator(6, "NAVALSUPPORT", "Economy & bonuses", KIND_LEVEL,
             "Naval support",
             "Naval support provided per ship. The Eye uses 2 = 'double the "
             "normal naval support'.",
             default=2, maximum=3),
    Variator(7, "MAXCITYSIZE", "Economy & bonuses", KIND_VALUE,
             "Max city size",
             "City population cap (growth limit). Not a starting-pop clamp — "
             "size-5 capitals survive a low value. Exact behaviour unverified.",
             default=20, maximum=99),
    Variator(8, "WONDERSEXPIRE", "Economy & bonuses", KIND_LEVEL,
             "Wonders expire",
             "Wonder obsolescence. Enlightenment uses 2 = 'wonders never go "
             "obsolete'.",
             default=2, maximum=2),
    Variator(9, "WARANDPEACE", "Advanced", KIND_LEVEL,
             "War & peace",
             "Diplomacy/war preset (exact effect not yet verified in-game).",
             maximum=3),
    Variator(10, "MUSTWINBY", "Victory", KIND_ENUM,
             "Must win by",
             "Restrict the game to a single victory type. Verified from the "
             "Victory Pack scenarios.",
             status="verified",
             options=[(0, "Any victory"), (2, "Space Race"),
                      (3, "Economic"), (4, "Cultural")]),
    Variator(11, "QUICKWIN", "Victory", KIND_LEVEL,
             "Quick win",
             "Lower the victory thresholds for a faster game (inferred).",
             maximum=3),
    Variator(12, "SPEEDMODE", "Economy & bonuses", KIND_FLAG,
             "Faster units",
             "Verified: +1 movement to ALL units (a settler shows '3 Moves' "
             "instead of 2). Not game speed.",
             status="verified", default=1, maximum=1),
    Variator(13, "UFOVISIT", "Advanced", KIND_LEVEL,
             "UFO visits",
             "Frequency of UFO visit events. The Eye uses 2.",
             maximum=3),
    Variator(14, "STARTERA", "Starting conditions", KIND_ENUM,
             "Starting era",
             "Starting tech era / unit tier (independent of the calendar "
             "year). Verified: 4 = Modern (Infantry/Tanks). Monotonic.",
             status="verified",
             options=[(0, "Ancient (default)"), (1, "Classical"),
                      (2, "Medieval"), (3, "Industrial"), (4, "Modern")]),
    Variator(15, "STARTSIZE", "Starting conditions", KIND_ENUM,
             "Starting cities",
             "Pre-built cities at game start. Verified: 1 → 1 city, 2 → 3 "
             "cities. Requires STARTYEAR on a fixed-map scenario. (3 is out of "
             "range and falls back to 1.)",
             status="verified",
             options=[(0, "Settler (none)"), (1, "1 city (capital)"),
                      (2, "3 cities")]),
    Variator(16, "CLIMATE", "Map generation", KIND_LEVEL,
             "Climate",
             "Climate preset (Ice Age uses 0). Only affects RANDOM maps.",
             maximum=3),
    Variator(17, "CANNOTWINBY", "Victory", KIND_ENUM,
             "Cannot win by",
             "Disable a single victory type (complement of Must-win-by).",
             options=[(0, "None disabled"), (2, "No Space Race"),
                      (3, "No Economic"), (4, "No Cultural")]),
    Variator(18, "NOSPACERACE", "Victory", KIND_FLAG,
             "No space race",
             "Disable the Space Race victory entirely.",
             maximum=1),
    Variator(19, "STARTGOLD", "Starting conditions", KIND_VALUE,
             "Starting gold",
             "Gold each civ starts with. Verified: value passes through "
             "literally (777 → 'Total Gold: 777').",
             status="verified", default=100, maximum=30000),
    Variator(20, "CARAVANGOLD", "Economy & bonuses", KIND_LEVEL,
             "Caravan gold",
             "Caravan delivery gold multiplier. Gold Rush uses 2.",
             default=2, maximum=3),
    Variator(21, "ATTACKBONUS", "Economy & bonuses", KIND_LEVEL,
             "Attack bonus",
             "Combat attack modifier (exact effect not yet verified in-game).",
             maximum=3),
    Variator(22, "GREATPEOPLERATE", "Economy & bonuses", KIND_LEVEL,
             "Great-people rate",
             "Great-person spawn rate. Hyper Drive uses 2.",
             default=2, maximum=3),
    Variator(23, "QUARTERPRICELIB", "Economy & bonuses", KIND_FLAG,
             "¼-price libraries",
             "Libraries and Universities cost a quarter as much (Hyper Drive).",
             default=1, maximum=1),
    Variator(24, "MOREGOLDRESOURCE", "Economy & bonuses", KIND_FLAG,
             "×4 gold/gem output",
             "Gold and Gem resources output four times as much (Gold Rush).",
             default=1, maximum=1),
    Variator(25, "MORETRADEPERERA", "Economy & bonuses", KIND_FLAG,
             "Bonus trade per era",
             "Extra trade income per era advanced (Gold Rush).",
             default=1, maximum=1),
    Variator(26, "DISPLAYCARD", "Advanced", KIND_BITMASK,
             "Pregame card",
             "Bitmask selecting the pregame info card (category + item index; "
             "e.g. cTECH=0x200, cPOWERUP=0x1000). Advanced — leave as-is "
             "unless you know the code.",
             default=0, maximum=65535),
    Variator(27, "STARTYEAR", "Starting conditions", KIND_VALUE,
             "Start year",
             "Sets the calendar year AND is the master switch that enables "
             "advanced starts (STARTSIZE/STARTLOC) on a fixed-map scenario. "
             "Negative = BC. Verified.",
             status="verified", default=1800, minimum=-4000, maximum=2100),
    Variator(28, "MAPNUMBER", "Map generation", KIND_VALUE,
             "Map number",
             "Force a specific built-in map (1–300) instead of random. Only "
             "meaningful for random-map (MAP=NONE) entries.",
             default=1, minimum=1, maximum=300),
    Variator(29, "STARTLOCME", "Starting conditions", KIND_COORD,
             "Player start tile",
             "Fixed starting tile for the human player. Requires STARTYEAR on "
             "a fixed-map scenario. Verified (seeds the whole starting "
             "cluster).",
             status="verified"),
    Variator(30, "STARTLOC0", "Starting conditions", KIND_COORD,
             "AI 1 start tile", "Fixed starting tile for the first AI civ.",
             status="verified"),
    Variator(31, "STARTLOC1", "Starting conditions", KIND_COORD,
             "AI 2 start tile", "Fixed starting tile for the second AI civ.",
             status="verified"),
    Variator(32, "STARTLOC2", "Starting conditions", KIND_COORD,
             "AI 3 start tile", "Fixed starting tile for the third AI civ.",
             status="verified"),
    Variator(33, "STARTLOC3", "Starting conditions", KIND_COORD,
             "AI 4 start tile", "Fixed starting tile for the fourth AI civ.",
             status="verified"),
    Variator(34, "STARTLOC4", "Starting conditions", KIND_COORD,
             "Spare start tile",
             "Fifth start slot — unused with the normal 1 player + 4 AI.",
             status="verified"),
]

VARIATORS: list[Variator] = _V
BY_NAME: dict[str, Variator] = {v.name: v for v in _V}
BY_INDEX: dict[int, Variator] = {v.index: v for v in _V}

# STARTLOC names, in "who" order, for the placement UI.
STARTLOC_NAMES = [
    "STARTLOCME", "STARTLOC0", "STARTLOC1",
    "STARTLOC2", "STARTLOC3", "STARTLOC4",
]
STARTLOC_LABELS = {
    "STARTLOCME": "Player",
    "STARTLOC0": "AI 1",
    "STARTLOC1": "AI 2",
    "STARTLOC2": "AI 3",
    "STARTLOC3": "AI 4",
    "STARTLOC4": "Spare",
}


def by_category(category: str) -> list[Variator]:
    return [v for v in _V if v.category == category]


# ── STARTLOC coordinate packing (display coords; verified) ───────────────────

def encode_startloc(row: int, col: int) -> int:
    """Pack a display-coord tile into a STARTLOC ``level`` value."""
    if not (0 <= row < 32 and 0 <= col < 32):
        raise ValueError(f"tile out of range: ({row}, {col})")
    return row * 256 + col


def decode_startloc(value: int) -> tuple[int, int]:
    """Unpack a STARTLOC ``level`` value into (row, col) display coords."""
    return (value >> 8) & 0xFF, value & 0xFF


def startloc_is_valid(value: int) -> bool:
    row, col = decode_startloc(value)
    return 0 <= row < 32 and 0 <= col < 32


# ── Combination validation (gates & exclusivity) ─────────────────────────────

def validate(values: dict, *, fixed_map: bool, model=None) -> list[tuple[str, str]]:
    """Check a set of chosen variators.

    ``values`` maps variator name → int (only present/enabled variators).
    ``fixed_map`` is True for a bundled-map scenario (Map Studio's case).
    ``model`` (optional MapModel) enables land-tile checks for STARTLOC.

    Returns a list of ``(status, message)`` where status is
    ``"warn"`` | ``"fail"`` (empty list = all good).
    """
    out: list[tuple[str, str]] = []

    has_year = "STARTYEAR" in values
    wants_advanced = [n for n in ("STARTSIZE", *STARTLOC_NAMES)
                      if n in values and values[n]]
    if fixed_map and wants_advanced and not has_year:
        out.append((
            "fail",
            "STARTSIZE / STARTLOC need STARTYEAR set on a fixed-map scenario "
            "— add a Start year or the pre-built start is ignored."))

    # STARTLOC requires STARTSIZE >= 1 to actually place cities.
    any_loc = [n for n in STARTLOC_NAMES if n in values]
    if any_loc and not values.get("STARTSIZE"):
        out.append((
            "warn",
            "STARTLOC tiles are set but STARTSIZE is 0 — with no starting "
            "cities the tiles only nudge the settler spawn."))

    # STARTLOC tiles must be land.
    if model is not None:
        for name in any_loc:
            row, col = decode_startloc(values[name])
            if not model.is_land(row, col):
                who = STARTLOC_LABELS[name]
                out.append((
                    "warn",
                    f"{who} start tile ({col}, {row}) is water/ice — the game "
                    "will reject it and use a scored spawn."))

    # Victory exclusivity.
    if values.get("MUSTWINBY") and values.get("CANNOTWINBY"):
        if values["MUSTWINBY"] == values["CANNOTWINBY"]:
            out.append((
                "fail",
                "Must-win-by and Cannot-win-by name the same victory type."))
    if values.get("MUSTWINBY") == 2 and values.get("NOSPACERACE"):
        out.append((
            "fail",
            "Must-win-by is Space Race but No-space-race is on."))

    return out
