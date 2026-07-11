#!/usr/bin/env python3
"""H10 — screenshot comparator.

Compare a candidate screenshot (from the port) against a reference screenshot
(from Xenia) and decide pass/fail at a tuned threshold. Used at milestones M4+
to turn "the menu renders" into a machine-checkable assertion.

Similarity = combination of structural (block-SSIM) and pixel (1 - normalized
RMSE) scores. Game frames have animated regions (menu shimmer, blinking prompts,
turn timers) that would sink a naive pixel diff, so:
  * SSIM is computed over 8x8 blocks and is robust to small intensity shifts;
  * --mask FILE excludes rectangles (one "x,y,w,h" per line, '#' comments) from
    BOTH scores, so known-animated regions don't cause false failures.

Only depends on Pillow + numpy (both already present on the host and easy to add
to the container). No scipy.

Usage:
    compare_screens.py REF CAND [--mask FILE] [--threshold 0.85]
                        [--metric combined|ssim|rmse] [--json OUT]
Exit: 0 = score >= threshold (match); 3 = below threshold (differ); 2 = error.
"""
import argparse
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError as e:                                    # pragma: no cover
    print(f'compare_screens: missing dependency: {e} (need Pillow + numpy)', file=sys.stderr)
    sys.exit(2)

BLOCK = 8
C1 = (0.01 * 255) ** 2
C2 = (0.03 * 255) ** 2


def load_gray(path):
    img = Image.open(path).convert('L')
    return img, np.asarray(img, dtype=np.float64)


def load_mask(path, shape):
    """Boolean array, True where pixels are VALID (not masked)."""
    valid = np.ones(shape, dtype=bool)
    if not path:
        return valid
    h, w = shape
    with open(path) as f:
        for raw in f:
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            try:
                x, y, rw, rh = (int(v) for v in line.replace(' ', '').split(','))
            except ValueError:
                print(f'compare_screens: bad mask line: {raw!r}', file=sys.stderr)
                continue
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(w, x + rw), min(h, y + rh)
            valid[y0:y1, x0:x1] = False
    return valid


def blockify(a):
    """Trim to a multiple of BLOCK and view as (nby, nbx, BLOCK, BLOCK)."""
    h, w = a.shape
    h -= h % BLOCK
    w -= w % BLOCK
    a = a[:h, :w]
    return (a.reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK)
             .transpose(0, 2, 1, 3)
             .reshape(h // BLOCK, w // BLOCK, BLOCK * BLOCK))


def block_ssim(a, b, valid):
    ba, bb = blockify(a), blockify(b)
    bv = blockify(valid.astype(np.float64))
    # a block counts only if it is (almost) fully valid
    block_ok = bv.mean(axis=2) > 0.5
    mu_a = ba.mean(axis=2); mu_b = bb.mean(axis=2)
    va = ba.var(axis=2); vb = bb.var(axis=2)
    cov = (ba * bb).mean(axis=2) - mu_a * mu_b
    ssim = (((2 * mu_a * mu_b + C1) * (2 * cov + C2)) /
            ((mu_a ** 2 + mu_b ** 2 + C1) * (va + vb + C2)))
    if not block_ok.any():
        return 1.0
    return float(ssim[block_ok].mean())


def norm_rmse(a, b, valid):
    d = (a - b)[valid]
    if d.size == 0:
        return 1.0
    rmse = float(np.sqrt(np.mean(d ** 2)))
    return max(0.0, 1.0 - rmse / 255.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('reference')
    ap.add_argument('candidate')
    ap.add_argument('--mask', help='rectangles to ignore: "x,y,w,h" per line')
    # Default 0.90 is a starting point. CALIBRATE with real frames (H2/H6): two
    # independent Xenia boots of the same scene should pass, and every known
    # animated region should be --mask'd rather than absorbed by lowering this.
    ap.add_argument('--threshold', type=float, default=0.90)
    ap.add_argument('--metric', choices=['combined', 'ssim', 'rmse'], default='combined')
    ap.add_argument('--json', help='write machine-readable result')
    args = ap.parse_args()

    try:
        ref_img, ref = load_gray(args.reference)
        cand_img, cand = load_gray(args.candidate)
    except Exception as e:
        print(f'compare_screens: cannot open images: {e}', file=sys.stderr)
        return 2

    if ref.shape != cand.shape:
        # Resize candidate to reference (a resolution mismatch is itself worth
        # noting, but we still want a score rather than a hard error).
        print(f'compare_screens: size mismatch ref{ref.shape[::-1]} '
              f'cand{cand.shape[::-1]}; resizing candidate', file=sys.stderr)
        cand_img = cand_img.resize(ref_img.size)
        cand = np.asarray(cand_img, dtype=np.float64)

    valid = load_mask(args.mask, ref.shape)
    ssim = block_ssim(ref, cand, valid)
    rmse = norm_rmse(ref, cand, valid)
    combined = 0.5 * ssim + 0.5 * rmse
    score = {'combined': combined, 'ssim': ssim, 'rmse': rmse}[args.metric]
    passed = score >= args.threshold

    masked_px = int((~valid).sum())
    print(f'ssim={ssim:.4f}  rmse_sim={rmse:.4f}  combined={combined:.4f}  '
          f'masked_px={masked_px}')
    print(f'metric={args.metric} score={score:.4f} threshold={args.threshold:.2f} '
          f'-> {"PASS" if passed else "FAIL"}')

    if args.json:
        import json
        with open(args.json, 'w') as f:
            json.dump({'ssim': ssim, 'rmse_sim': rmse, 'combined': combined,
                       'metric': args.metric, 'score': score,
                       'threshold': args.threshold, 'passed': passed,
                       'masked_px': masked_px}, f, indent=2)

    return 0 if passed else 3


if __name__ == '__main__':
    sys.exit(main())
