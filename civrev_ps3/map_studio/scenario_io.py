"""Read/write scenario VARIATORs in a Pak's dlcscenariodata{N}.xml.

The shipped XML is ISO-8859-1 with CRLF line endings and (in the installed
edat form) can carry trailing NUL padding. We must not corrupt any of that, so
writes are surgical: we replace only the ``<VARIATOR>…</VARIATOR>`` span of the
target ``<EntryInfo>`` and leave every other byte untouched.

A scenario map slot is matched to its XML entry by the ``<MAP>`` value, which
equals the slot's ``tag`` (e.g. ``The_UK``).

This mirrors the standalone rpcs3_automation/set_variators.py, kept separate so
Map Studio has no dependency on the automation harness.
"""

from __future__ import annotations

import re
from pathlib import Path

_ENTRY_RE = re.compile(r"<EntryInfo>.*?</EntryInfo>", re.S)
_VAR_BLOCK_RE = re.compile(r"<VARIATOR>.*</VARIATOR>", re.S)   # greedy: whole span
_SPEC_RE = re.compile(r'text="(.*?)"\s+level="(.*?)"')


def _decode(raw: bytes) -> tuple[str, bool]:
    """Return (text, had_nul). Strips NULs for parsing; we re-pad on write."""
    had_nul = b"\x00" in raw
    return raw.replace(b"\x00", b"").decode("iso-8859-1"), had_nul


def find_xml(pak_dir: Path) -> Path:
    xmls = sorted(Path(pak_dir).glob("dlcscenariodata*.xml"))
    if not xmls:
        raise FileNotFoundError(f"no dlcscenariodata*.xml in {pak_dir}")
    return xmls[0]


def _entry_for_map(text: str, map_tag: str) -> str | None:
    for m in _ENTRY_RE.finditer(text):
        e = m.group(0)
        mm = re.search(r"<MAP>(.*?)</MAP>", e)
        if mm and mm.group(1).strip() == map_tag:
            return e
    return None


def read_variators(pak_dir: Path, map_tag: str) -> dict[str, int]:
    """Return {VARIATOR_NAME: int_value} for the entry whose MAP == map_tag."""
    text, _ = _decode(find_xml(pak_dir).read_bytes())
    entry = _entry_for_map(text, map_tag)
    if entry is None:
        return {}
    out: dict[str, int] = {}
    for name, level in _SPEC_RE.findall(entry):
        try:
            out[name] = int(level)
        except ValueError:
            continue
    return out


def entry_meta(pak_dir: Path, map_tag: str) -> dict:
    """Return {'type','mp','id','title'} for the entry, for display."""
    text, _ = _decode(find_xml(pak_dir).read_bytes())
    entry = _entry_for_map(text, map_tag) or ""
    def grab(tag, default=""):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", entry, re.S)
        return m.group(1).strip() if m else default
    return {
        "type": grab("EntryType"),
        "mp": grab("bMultiplayer"),
        "id": grab("ID"),
        "title": grab("ENG"),
    }


def _render_variators(values: dict[str, int]) -> str:
    """Render one <VARIATOR> block per spec, matching the authored style.

    Order follows the schema enum index so writes are stable/diff-friendly.
    """
    from scenario_schema import BY_NAME

    items = sorted(values.items(),
                   key=lambda kv: BY_NAME[kv[0]].index if kv[0] in BY_NAME
                   else 999)
    blocks = [
        f'<VARIATOR>\r\n\t\t\t<specs text="{name}" level="{int(val)}"/>\r\n\t\t</VARIATOR>'
        for name, val in items
    ]
    return "\r\n\t\t".join(blocks)


def write_variators(pak_dir: Path, map_tag: str, values: dict[str, int]) -> None:
    """Replace the target entry's VARIATOR block with ``values``.

    Preserves encoding, CRLF, and NUL padding of the rest of the file. Raises
    if the entry or its VARIATOR block cannot be located.
    """
    xml_path = find_xml(pak_dir)
    raw = xml_path.read_bytes()
    text, had_nul = _decode(raw)

    entry = _entry_for_map(text, map_tag)
    if entry is None:
        raise ValueError(f"no <EntryInfo> with <MAP>{map_tag}</MAP>")
    if not _VAR_BLOCK_RE.search(entry):
        raise ValueError(f"entry for {map_tag} has no <VARIATOR> block to replace")

    new_block = _render_variators(values)
    new_entry = _VAR_BLOCK_RE.sub(lambda _m: new_block, entry, count=1)
    new_text = text.replace(entry, new_entry, 1)

    if new_text == text:
        # No structural change (e.g. identical values) — still rewrite to be
        # explicit, but this is a no-op guard against silent failures.
        return

    out = new_text.encode("iso-8859-1")
    if had_nul:
        # Preserve original total length by re-padding with NULs, matching how
        # the installed edat form was stored.
        if len(out) < len(raw):
            out += b"\x00" * (len(raw) - len(out))
    xml_path.write_bytes(out)


def verify_written(pak_dir: Path, map_tag: str, values: dict[str, int]) -> bool:
    """Re-read the file and confirm it holds exactly ``values``."""
    got = read_variators(pak_dir, map_tag)
    return got == {k: int(v) for k, v in values.items()}
