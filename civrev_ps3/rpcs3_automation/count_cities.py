#!/usr/bin/env python3
"""Count distinct player cities across cycle-capture frames via OCR.

Reads debug_*_spawn_view.png + debug_*_cycle_*.png frames, OCRs each frame's
city-name banner region (the green-crowned label near screen center) plus the
bottom-left unit panel and bottom-right year, and reports the distinct city
names seen. Used for STARTSIZE/STARTLOC factorial runs.

Usage: count_cities.py [frames_dir] [--label RUNLABEL]
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
from PIL import Image
import pytesseract

KNOWN_RUSSIAN_CITIES = {
    "moscow", "riga", "sverdlovsk", "rostov", "sevastopol", "odessa",
    "novgorod", "kiev", "leningrad", "stalingrad", "minsk", "smolensk",
    "petersburg", "kharkov", "vladivostok", "magnitogorsk", "murmansk",
    "tashkent", "omsk", "samara", "kazan", "yakutsk", "irkutsk", "krasnoyarsk",
}


def ocr(img: Image.Image, psm: int = 11) -> str:
    return pytesseract.image_to_string(img, config=f"--psm {psm}")


def analyze_frame(path: str) -> dict:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if "_census_" in os.path.basename(path):
        # City Screen: name is large near the top — OCR the top band too
        top = im.crop((0, 0, w, int(h * 0.3)))
        top = top.resize((top.width * 2, top.height * 2))
        top_text = ocr(top, psm=6)
        cities = {t.title() for t in re.findall(r"[A-Za-z]+", top_text)
                  if t.lower() in KNOWN_RUSSIAN_CITIES}
        return {"file": os.path.basename(path), "cities": cities,
                "year": None, "unit": None}
    # City banner appears in the middle band of the screen; unit panel bottom
    # left; year bottom right. OCR middle band at 2x for small text.
    mid = im.crop((0, int(h * 0.25), w, int(h * 0.75)))
    mid = mid.resize((mid.width * 2, mid.height * 2))
    mid_text = ocr(mid)
    bottom = im.crop((0, int(h * 0.72), w, h))
    bottom_text = ocr(bottom, psm=6)

    cities = set()
    for token in re.findall(r"[A-Za-z]+", mid_text):
        if token.lower() in KNOWN_RUSSIAN_CITIES:
            cities.add(token.title())
    year = None
    m = re.search(r"(\d{3,4})\s*(BC|AD|BE|AO|A0)", bottom_text)
    if m:
        year = f"{m.group(1)} {'BC' if m.group(2) == 'BE' else 'AD' if m.group(2) in ('AO', 'A0') else m.group(2)}"
    unit = None
    for u in ("Settlers", "Pikemen", "Warrior", "Archers", "Legion", "Knights",
              "Riflemen", "Militia"):
        if u.lower() in bottom_text.lower() or u.lower() in mid_text.lower():
            unit = u
            break
    return {"file": os.path.basename(path), "cities": cities, "year": year,
            "unit": unit}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir", nargs="?",
                    default=os.path.join(os.path.dirname(__file__), "output"))
    ap.add_argument("--label", default="run")
    args = ap.parse_args()

    frames = sorted(
        glob.glob(os.path.join(args.frames_dir, "debug_*_spawn_view.png"))
        + glob.glob(os.path.join(args.frames_dir, "debug_*_cycle_*.png"))
        + glob.glob(os.path.join(args.frames_dir, "debug_*_census_*.png"))
    )
    if not frames:
        sys.exit(f"no spawn/cycle frames in {args.frames_dir}")

    all_cities: set[str] = set()
    years: set[str] = set()
    units: set[str] = set()
    for f in frames:
        info = analyze_frame(f)
        all_cities |= info["cities"]
        if info["year"]:
            years.add(info["year"])
        if info["unit"]:
            units.add(info["unit"])
        tag = ",".join(sorted(info["cities"])) or "-"
        print(f"  {info['file']:36s} cities={tag:24s} unit={info['unit'] or '-':9s} year={info['year'] or '-'}")

    print(f"\n[{args.label}] DISTINCT CITIES ({len(all_cities)}): "
          f"{sorted(all_cities) or 'NONE'} | units={sorted(units)} | years={sorted(years)}")


if __name__ == "__main__":
    main()
