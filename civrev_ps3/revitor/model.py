"""Map data model — 32x32 tile grid with terrain, rivers, and spawn markers.

Storage is in display (row-major) coordinates; .map files are column-major
(display[r][c] = file[c][r]) with a 64-byte 0xFF footer.

Tile byte layout (verified against EBOOT + shipped assets):
  bits 0-2  terrain type (0=Ocean 1=Grassland 2=Plains 3=Hills 4=Forest
                          5=Desert 6=Mountains 7=Ice)
  bit 4     0x10 spawn marker (multiplayer only)
  bit 5     0x20 river on west edge
  bit 6     0x40 river on east edge
  bit 7     0x80 river on south edge
"""

from pathlib import Path

GRID = 32
MAP_BYTES = GRID * GRID          # 1024
FILE_SIZE = MAP_BYTES + 64       # 1088

OCEAN, GRASSLAND, PLAINS, HILLS, FOREST, DESERT, MOUNTAINS, ICE = range(8)

TERRAIN_NAMES = [
    "Ocean", "Grassland", "Plains", "Hills",
    "Forest", "Desert", "Mountains", "Ice",
]

LAND_TYPES = {GRASSLAND, PLAINS, HILLS, FOREST, DESERT, MOUNTAINS}

DLC_SLOTS = [
    {"tag": "The_World", "id": 28, "title": "Earth", "file": "the_world.map"},
    {"tag": "Equal_Opportunity", "id": 29, "title": "Equal Opportunity",
     "file": "equal_opportunity.map"},
    {"tag": "South_Pacific", "id": 30, "title": "South Pacific",
     "file": "south_pacific.map"},
    {"tag": "The_UK", "id": 31, "title": "The United Kingdom",
     "file": "the_uk.map"},
]


def display_to_file(data: bytes | bytearray) -> bytearray:
    """Convert 1024 display-order bytes to file order + footer (1088 bytes)."""
    out = bytearray(FILE_SIZE)
    for r in range(GRID):
        for c in range(GRID):
            out[c * GRID + r] = data[r * GRID + c]
    out[MAP_BYTES:] = b"\xff" * 64
    return out


def file_to_display(raw: bytes) -> bytearray:
    """Convert file-order .map bytes (>=1024) to display order (1024 bytes)."""
    if len(raw) < MAP_BYTES:
        raise ValueError(f"Map data too small: {len(raw)} bytes (need {MAP_BYTES})")
    out = bytearray(MAP_BYTES)
    for r in range(GRID):
        for c in range(GRID):
            out[r * GRID + c] = raw[c * GRID + r]
    return out


class MapModel:
    """Tile grid plus edit metadata (dirty flag, source description)."""

    def __init__(self):
        self.data = bytearray(MAP_BYTES)
        self.dirty = False

    # ── Tile access ─────────────────────────────────────────

    def get_tile(self, row: int, col: int) -> int:
        return self.data[row * GRID + col]

    def set_tile(self, row: int, col: int, val: int):
        i = row * GRID + col
        v = val & 0xFF
        if self.data[i] != v:
            self.data[i] = v
            self.dirty = True

    def get_terrain(self, row: int, col: int) -> int:
        return self.get_tile(row, col) & 0x07

    def set_terrain(self, row: int, col: int, terrain: int):
        old = self.get_tile(row, col)
        self.set_tile(row, col, (old & 0xF8) | (terrain & 0x07))

    def is_land(self, row: int, col: int) -> bool:
        return self.get_terrain(row, col) in LAND_TYPES

    def get_rivers(self, row: int, col: int) -> dict:
        v = self.get_tile(row, col)
        return {"west": bool(v & 0x20), "east": bool(v & 0x40), "south": bool(v & 0x80)}

    def set_river(self, row: int, col: int, flag: str, on: bool):
        mask = {"west": 0x20, "east": 0x40, "south": 0x80}[flag]
        old = self.get_tile(row, col)
        self.set_tile(row, col, (old | mask) if on else (old & ~mask))

    def toggle_river(self, row: int, col: int, flag: str):
        self.set_river(row, col, flag, not self.get_rivers(row, col)[flag])

    def has_spawn(self, row: int, col: int) -> bool:
        return bool(self.get_tile(row, col) & 0x10)

    def set_spawn(self, row: int, col: int, on: bool):
        old = self.get_tile(row, col)
        self.set_tile(row, col, (old | 0x10) if on else (old & ~0x10))

    # ── Snapshots (undo/redo) ───────────────────────────────

    def snapshot(self) -> bytes:
        return bytes(self.data)

    def restore(self, snap: bytes):
        if bytes(self.data) != snap:
            self.data[:] = snap
            self.dirty = True

    # ── File I/O ────────────────────────────────────────────

    def load_file(self, path: Path):
        self.data[:] = file_to_display(path.read_bytes())
        self.dirty = False

    def load_bytes(self, raw: bytes):
        self.data[:] = file_to_display(raw)
        self.dirty = False

    def save_file(self, path: Path):
        path.write_bytes(bytes(display_to_file(self.data)))
        self.dirty = False

    def to_file_bytes(self) -> bytes:
        return bytes(display_to_file(self.data))

    # ── Whole-map operations ────────────────────────────────

    def flood_fill(self, row: int, col: int, terrain: int):
        old_terrain = self.get_terrain(row, col)
        if old_terrain == terrain:
            return
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if not (0 <= r < GRID and 0 <= c < GRID):
                continue
            if self.get_terrain(r, c) != old_terrain:
                continue
            self.set_terrain(r, c, terrain)
            stack.extend([(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)])

    def clear(self):
        """Reset to ocean with ice borders on the polar rows."""
        self.data[:] = b"\x00" * MAP_BYTES
        for c in range(GRID):
            for r in (0, 1, 30, 31):
                self.data[r * GRID + c] = ICE
        self.dirty = True

    def mirror_horizontal(self):
        """Mirror left-right. East/west river flags swap sides."""
        out = bytearray(MAP_BYTES)
        for r in range(GRID):
            for c in range(GRID):
                v = self.data[r * GRID + (GRID - 1 - c)]
                w, e = bool(v & 0x20), bool(v & 0x40)
                v = (v & ~0x60) | (0x40 if w else 0) | (0x20 if e else 0)
                out[r * GRID + c] = v
        self.data[:] = out
        self.dirty = True

    def mirror_vertical(self):
        """Mirror top-bottom. South-edge rivers become the south edge of the
        tile that now sits above the old edge position, so shift them."""
        out = bytearray(MAP_BYTES)
        for r in range(GRID):
            for c in range(GRID):
                out[r * GRID + c] = self.data[(GRID - 1 - r) * GRID + c] & ~0x80
        # Re-place south rivers: an edge below old row r is above new row
        # (GRID-1-r), i.e. the south edge of new row (GRID-2-r).
        for r in range(GRID):
            for c in range(GRID):
                if self.data[r * GRID + c] & 0x80:
                    nr = GRID - 2 - r
                    if 0 <= nr < GRID:
                        out[nr * GRID + c] |= 0x80
        self.data[:] = out
        self.dirty = True

    def shift(self, dr: int, dc: int):
        """Shift the map with wraparound (rivers/spawns move with tiles)."""
        out = bytearray(MAP_BYTES)
        for r in range(GRID):
            for c in range(GRID):
                sr = (r - dr) % GRID
                sc = (c - dc) % GRID
                out[r * GRID + c] = self.data[sr * GRID + sc]
        self.data[:] = out
        self.dirty = True

    def bresenham(self, r0, c0, r1, c1):
        tiles = []
        dx, dy = abs(c1 - c0), abs(r1 - r0)
        sx = 1 if c0 < c1 else -1
        sy = 1 if r0 < r1 else -1
        err = dx - dy
        while True:
            tiles.append((r0, c0))
            if r0 == r1 and c0 == c1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                c0 += sx
            if e2 < dx:
                err += dx
                r0 += sy
        return tiles

    # ── Statistics & validation ─────────────────────────────

    def stats(self) -> dict:
        counts = [0] * 8
        land_rivers = 0
        ocean_rivers = 0
        spawns = 0
        spawns_on_land = 0
        for v in self.data:
            t = v & 0x07
            counts[t] += 1
            if v & 0xE0:
                if t in LAND_TYPES:
                    land_rivers += 1
                else:
                    ocean_rivers += 1
            if v & 0x10:
                spawns += 1
                if t in LAND_TYPES:
                    spawns_on_land += 1
        land = sum(counts[t] for t in LAND_TYPES)
        return {
            "terrain_counts": counts,
            "land": land,
            "ocean": counts[OCEAN],
            "ice": counts[ICE],
            "rivers": land_rivers + ocean_rivers,
            "land_rivers": land_rivers,
            "ocean_rivers": ocean_rivers,
            "spawns": spawns,
            "spawns_on_land": spawns_on_land,
        }

    def validate(self) -> list:
        """Return (status, message) tuples. status: 'pass' | 'warn' | 'fail'."""
        checks = []
        s = self.stats()

        if s["land"] == 0:
            checks.append(("fail", "No land tiles — map is unplayable"))
        elif s["land"] < 60:
            checks.append(("warn", f"Only {s['land']} land tiles — very cramped"))
        else:
            checks.append(("pass", f"{s['land']} land tiles"))

        if s["land"] > 0:
            if s["land_rivers"] == 0:
                checks.append(("fail",
                               "No rivers on land — settlers will spawn on ice"))
            elif s["land_rivers"] < 4:
                checks.append(("warn",
                               f"Only {s['land_rivers']} river tiles on land — "
                               "add more for reliable spawns"))
            else:
                checks.append(("pass", f"{s['land_rivers']} land tiles with rivers"))

        if s["ocean_rivers"] > 0:
            checks.append(("warn",
                           f"{s['ocean_rivers']} river flags on ocean/ice — "
                           "has no effect"))

        border_ok = all(
            self.get_terrain(r, c) == ICE
            for c in range(GRID) for r in (0, 1, 30, 31)
        )
        checks.append(
            ("pass", "Polar ice borders intact (rows 0–1, 30–31)")
            if border_ok
            else ("warn", "Polar ice borders broken — originals always keep "
                          "rows 0–1 and 30–31 as ice")
        )

        if s["spawns"] > 0:
            if s["spawns_on_land"] < s["spawns"]:
                checks.append(("warn",
                               f"{s['spawns'] - s['spawns_on_land']} spawn "
                               "markers on water/ice"))
            else:
                checks.append(("pass",
                               f"{s['spawns']} spawn markers (multiplayer)"))
        else:
            checks.append(("warn", "No spawn markers — fine for single-player"))

        return checks

    def changed_tiles(self, reference: bytes) -> list:
        """Tiles whose terrain differs from a reference display-order grid.

        Only terrain bits matter for texture regeneration — river/spawn flags
        don't affect the baked DDS art.
        """
        out = []
        for r in range(GRID):
            for c in range(GRID):
                i = r * GRID + c
                if (self.data[i] & 0x07) != (reference[i] & 0x07):
                    out.append((r, c))
        return out
