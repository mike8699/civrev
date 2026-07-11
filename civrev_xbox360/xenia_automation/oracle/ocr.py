#!/usr/bin/env python3
"""OCR an image (via the `tesseract` binary) and test for a text pattern.

Used by run_scenario.sh `wait_text` / `find_text` to wait for or scroll to an
on-screen prompt — more robust than fixed sleeps or fixed D-pad counts.

The image is upscaled 2x and autocontrasted first so tesseract can read the
game's stylized, low-contrast text that it otherwise garbles.

--crop L,T,R,B restricts OCR to a sub-region (fractions 0..1 of width/height).
This is how selection is verified: a menu's SELECTED item shows its name in a
fixed panel (scenario description, civ description), so OCR-ing only that panel
matches when the item is *selected*, not merely visible elsewhere in a list.

Usage: ocr.py <image> <pattern> [--crop L,T,R,B]
Exit 0 if the pattern (case-insensitive regex) is found (prints matched text),
1 if not found, 2 on error.
"""
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageOps


def main() -> int:
    args = sys.argv[1:]
    crop = None
    if "--crop" in args:
        i = args.index("--crop")
        try:
            crop = tuple(float(v) for v in args[i + 1].split(","))
        except (IndexError, ValueError):
            print("bad --crop L,T,R,B", file=sys.stderr)
            return 2
        del args[i:i + 2]
    if len(args) < 2:
        print("usage: ocr.py <image> <pattern> [--crop L,T,R,B]", file=sys.stderr)
        return 2
    img_path, pattern = args[0], args[1]
    tmp = None
    try:
        im = Image.open(img_path).convert("L")
        if crop:
            w, h = im.size
            im = im.crop((int(crop[0] * w), int(crop[1] * h),
                          int(crop[2] * w), int(crop[3] * h)))
        im = ImageOps.autocontrast(im.resize((im.width * 2, im.height * 2)))
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        im.save(tmp)
        r = subprocess.run(["tesseract", tmp, "stdout"],
                           capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print("ocr error: tesseract not installed", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("ocr error: tesseract timed out", file=sys.stderr)
        return 2
    except Exception as e:                                      # pragma: no cover
        print(f"ocr error: {e}", file=sys.stderr)
        return 2
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    if re.search(pattern, r.stdout, re.IGNORECASE):
        print(" ".join(r.stdout.split())[:100])
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
