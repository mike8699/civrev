#!/usr/bin/env python3
"""Calibration/regression test for compare_screens.py using synthetic frames.
No Docker/GPU needed. Verifies the comparator's decision boundaries and the
mask mechanism — the robust invariants the tool actually contracts to (a knife-
edge between benign jitter and a small expected animation is intentionally NOT
a threshold decision; that is what --mask is for):

  identical             -> PASS
  realistic two-boot jitter (light blur + small shift) -> PASS
  black / garbage frame -> FAIL
  large divergent region, unmasked -> FAIL
  same region, masked   -> PASS   (masking restores the score)
  monotonicity          -> score(jitter) > score(divergent)

Exit 0 iff all invariants hold.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
CMP = os.path.join(HERE, 'compare_screens.py')
W, H = 320, 240


def synth(seed=0):
    """A structured pseudo-game frame: gradient + UI panels + a text-like bar."""
    yy, xx = np.mgrid[0:H, 0:W]
    a = ((xx * 0.4 + yy * 0.3) % 256).astype(np.uint8)
    a[40:120, 40:200] = 200
    a[60:80, 60:180] = 30
    a[150:200, 100:260] = 120
    return a


def run(ref, cand, *extra):
    r = subprocess.run([sys.executable, CMP, ref, cand, *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def score_of(out):
    for tok in out.split():
        if tok.startswith('combined='):
            return float(tok.split('=', 1)[1])
    return None


def main():
    tmp = tempfile.mkdtemp()
    base = synth()
    Image.fromarray(base).save(f'{tmp}/ref.png')

    Image.fromarray(base).save(f'{tmp}/same.png')

    # realistic two-boot jitter: light blur + small brightness shift + tiny noise
    jit = Image.fromarray(base).filter(ImageFilter.GaussianBlur(0.4))
    jit = np.clip(np.asarray(jit, int) + 2 +
                  np.random.default_rng(2).integers(-2, 3, base.shape), 0, 255).astype(np.uint8)
    Image.fromarray(jit).save(f'{tmp}/jitter.png')

    Image.fromarray(np.zeros_like(base)).save(f'{tmp}/black.png')

    # large divergent region (10% of frame) in 100,150..260,200
    big = base.copy(); big[150:200, 100:260] = 240
    Image.fromarray(big).save(f'{tmp}/big.png')

    maskfile = f'{tmp}/mask.txt'
    with open(maskfile, 'w') as f:
        f.write('# ignore the divergent panel\n100,150,160,50\n')

    fails = 0

    def expect(name, rc, want):
        nonlocal fails
        ok = (rc == want)
        print(f'[{"OK" if ok else "FAIL"}] {name}: rc={rc} (want {want})')
        fails += (0 if ok else 1)

    rc, _ = run(f'{tmp}/ref.png', f'{tmp}/same.png', '--threshold', '0.90')
    expect('identical -> PASS', rc, 0)

    rc, out_jit = run(f'{tmp}/ref.png', f'{tmp}/jitter.png', '--threshold', '0.90')
    expect('two-boot jitter -> PASS', rc, 0)

    rc, _ = run(f'{tmp}/ref.png', f'{tmp}/black.png', '--threshold', '0.90')
    expect('black frame -> FAIL', rc, 3)

    rc, out_big = run(f'{tmp}/ref.png', f'{tmp}/big.png', '--threshold', '0.92')
    expect('divergent region, unmasked -> FAIL', rc, 3)

    rc, _ = run(f'{tmp}/ref.png', f'{tmp}/big.png', '--threshold', '0.92', '--mask', maskfile)
    expect('divergent region, masked -> PASS', rc, 0)

    sj, sb = score_of(out_jit), score_of(out_big)
    mono = sj is not None and sb is not None and sj > sb
    print(f'[{"OK" if mono else "FAIL"}] monotonicity: jitter {sj} > divergent {sb}')
    fails += (0 if mono else 1)

    print('ALL COMPARATOR TESTS PASSED' if fails == 0 else f'{fails} COMPARATOR TEST(S) FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
