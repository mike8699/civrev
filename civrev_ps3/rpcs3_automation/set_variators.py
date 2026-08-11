#!/usr/bin/env python3
"""Set a scenario entry's VARIATOR block in a Pak DLC XML, repack, install, verify.

Used for runtime variator experiments (SCENARIO_VARIATORS.md). Always
re-extracts the installed edat and re-parses the variators to guard against
silent edit failures (a sed one-liner once failed silently and burned a boot).

Usage:
  set_variators.py --pak Pak7 --entry SCENARIO_GLOBAL_WARMING \
      DISPLAYCARD=542 STARTERA=2 STARTSIZE=2 STARTYEAR=1800
  set_variators.py --pak Pak7 --entry SCENARIO_GLOBAL_WARMING --restore
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # civrev_ps3/
VENV_PY = REPO.parent / ".venv" / "bin" / "python"
USRDIR = Path.home() / ".config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR"

PRISTINE = {
    # entry tag -> authored variator list, for --restore
    "SCENARIO_GLOBAL_WARMING": [
        ("BAGRESSIVE", "2"), ("BFECUNDITY", "2"), ("BARBVSGOODY", "1"),
        ("RESOURCEDENSITY", "1"), ("STARTYEAR", "1800"), ("STARTERA", "2"),
        ("STARTSIZE", "2"), ("DISPLAYCARD", "542"),
    ],
    "SCENARIO_EYE": [
        ("NAVALSUPPORT", "2"), ("SPEEDMODE", "1"), ("UFOVISIT", "2"),
        ("DISPLAYCARD", "4104"),
    ],
    "SCENARIO_ICEWORLD": [
        ("BFECUNDITY", "2"), ("BARBVSGOODY", "2"), ("CLIMATE", "0"),
        ("DISPLAYCARD", "4359"),
    ],
}


def find_xml(pak_dir: Path) -> Path:
    xmls = sorted(pak_dir.glob("dlcscenariodata*.xml"))
    if not xmls:
        sys.exit(f"no dlcscenariodata*.xml in {pak_dir}")
    return xmls[0]


def parse_entry(xml_text: str, entry_tag: str) -> str:
    m = re.search(
        r"<EntryInfo>(?:(?!</EntryInfo>).)*" + re.escape(entry_tag) + r".*?</EntryInfo>",
        xml_text, re.S)
    if not m:
        sys.exit(f"entry {entry_tag} not found")
    return m.group(0)


def set_variators(xml_text: str, entry_tag: str, specs: list[tuple[str, str]]) -> str:
    # Authored style: one <VARIATOR> block per spec. Replace the whole span
    # from the first <VARIATOR> to the last </VARIATOR> in the entry.
    newvar = "\r\n\t\t".join(
        f'<VARIATOR>\r\n\t\t\t<specs text="{k}" level="{v}"/>\r\n\t\t</VARIATOR>'
        for k, v in specs
    )

    def fix(m):
        e = m.group(0)
        if entry_tag not in e:
            return e
        return re.sub(r"<VARIATOR>.*</VARIATOR>", newvar, e, flags=re.S)  # greedy: whole span

    # sanity: the entry must exist (the installed-edat verify below is the
    # real guard against silent edit failures)
    parse_entry(xml_text, entry_tag)
    return re.sub(r"<EntryInfo>.*?</EntryInfo>", fix, xml_text, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pak", required=True, help="pak dir name, e.g. Pak7")
    ap.add_argument("--entry", required=True, help="EntryTag, e.g. SCENARIO_GLOBAL_WARMING")
    ap.add_argument("--restore", action="store_true", help="restore authored variators")
    ap.add_argument("specs", nargs="*", help="NAME=VALUE pairs")
    args = ap.parse_args()

    pak_dir = REPO / args.pak
    xml_path = find_xml(pak_dir)

    if args.restore:
        specs = PRISTINE[args.entry]
    else:
        specs = [tuple(s.split("=", 1)) for s in args.specs]
        if not specs:
            sys.exit("no NAME=VALUE specs given (or use --restore)")

    text = xml_path.read_bytes().decode("iso-8859-1")
    text = set_variators(text, args.entry, specs)
    xml_path.write_bytes(text.encode("iso-8859-1"))

    # repack + install
    subprocess.run([str(VENV_PY), str(REPO / "fpk.py"), "repack", str(pak_dir)],
                   check=True, capture_output=True)
    fpk_file = REPO / f"{args.pak}.FPK"
    edat = USRDIR / f"{args.pak}.edat"
    shutil.copy(fpk_file, edat)

    # verify: re-extract installed edat, reparse variators
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp_fpk = Path(td) / "check.FPK"
        shutil.copy(edat, tmp_fpk)
        # fpk.py extracts to <cwd>/<stem>/ — run with cwd=td
        subprocess.run([str(VENV_PY), str(REPO / "fpk.py"), "extract", str(tmp_fpk)],
                       check=True, capture_output=True, cwd=td)
        out_xml = find_xml(Path(td) / "check")
        entry = parse_entry(
            out_xml.read_bytes().replace(b"\x00", b"").decode("iso-8859-1"),
            args.entry)
        installed = re.findall(r'text="(.*?)" level="(.*?)"', entry)

    if installed != [(k, v) for k, v in specs]:
        sys.exit(f"VERIFY FAILED: installed={installed} wanted={specs}")
    print(f"OK: {args.pak}.edat installed, {args.entry} variators = {installed}")


if __name__ == "__main__":
    main()
