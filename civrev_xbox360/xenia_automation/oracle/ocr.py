#!/usr/bin/env python3
"""OCR an image (via the `tesseract` binary) and test for a text pattern.

Used by run_scenario.sh `wait_text` to wait for a specific on-screen prompt
(e.g. "Press START") before acting — more robust than fixed sleeps, since it
adapts to boot speed and detects the exact UI state.

The image is upscaled 2x and autocontrasted first, which lets tesseract read the
game's stylized, low-contrast prompt text (e.g. "Press START to begin") that it
otherwise garbles. Needs the `tesseract` binary + PIL (no pytesseract) — both
apt-available, so it runs identically host-side or in the container.

Usage: ocr.py <image> <pattern>
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
    if len(sys.argv) < 3:
        print("usage: ocr.py <image> <pattern>", file=sys.stderr)
        return 2
    img_path, pattern = sys.argv[1], sys.argv[2]
    tmp = None
    try:
        im = Image.open(img_path).convert("L")
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
