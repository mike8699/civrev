#!/usr/bin/env python3
"""Virtual Xbox 360 controller (uinput) for driving Xenia's hid="sdl" input.

Xenia's SDL HID reads game controllers, NOT the keyboard — so xdotool keystrokes
never reach the game. This creates a uinput device that presents as a Microsoft
Xbox 360 pad (vendor 0x045e / product 0x028e), which SDL auto-maps via its
built-in Xbox 360 mapping. Xenia then binds it to emulated controller slot 0 and
the game receives real controller input.

Runs as a daemon inside the container, reading one command per line from a FIFO
(default /tmp/virtpad.cmd) so the host can drive it via `docker exec`:

  press <BTN> [secs]     tap a button (default 0.08s)
  down  <BTN>            press and hold
  up    <BTN>            release
  dpad  <up|down|left|right|center>
  stick <l|r> <x> <y>    axis -32768..32767
  trig  <l|r> <0..255>
  sleep <secs>

BTN: A B X Y LB RB START BACK GUIDE LS RS
Needs: python3-evdev, writable /dev/uinput (privileged container).
"""
import glob
import os
import stat
import sys
import time

from evdev import UInput, AbsInfo, ecodes as e


def ensure_dev_node():
    """Containers have no udev, so a freshly-created uinput device has no
    /dev/input/eventN node — SDL reads /dev/input/event*, so without the node the
    controller is invisible. Create it by hand from sysfs (major:minor)."""
    for evdir in glob.glob('/sys/class/input/event*'):
        ev = os.path.basename(evdir)
        try:
            name = open(os.path.join(evdir, 'device', 'name')).read().strip()
        except OSError:
            continue
        if 'X-Box 360 pad' not in name:
            continue
        node = f'/dev/input/{ev}'
        if not os.path.exists(node):
            major, minor = open(os.path.join(evdir, 'dev')).read().strip().split(':')
            os.makedirs('/dev/input', exist_ok=True)
            try:
                os.mknod(node, 0o660 | stat.S_IFCHR, os.makedev(int(major), int(minor)))
            except (FileExistsError, PermissionError) as ex:
                sys.stderr.write(f'[virtpad] mknod {node} failed: {ex}\n')
        return node
    return None

BTN = {
    'A': e.BTN_A, 'B': e.BTN_B, 'X': e.BTN_X, 'Y': e.BTN_Y,
    'LB': e.BTN_TL, 'RB': e.BTN_TR, 'BACK': e.BTN_SELECT, 'START': e.BTN_START,
    'GUIDE': e.BTN_MODE, 'LS': e.BTN_THUMBL, 'RS': e.BTN_THUMBR,
}

CAP = {
    e.EV_KEY: list(BTN.values()),
    e.EV_ABS: [
        (e.ABS_X,   AbsInfo(0, -32768, 32767, 16, 128, 0)),
        (e.ABS_Y,   AbsInfo(0, -32768, 32767, 16, 128, 0)),
        (e.ABS_RX,  AbsInfo(0, -32768, 32767, 16, 128, 0)),
        (e.ABS_RY,  AbsInfo(0, -32768, 32767, 16, 128, 0)),
        (e.ABS_Z,   AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_RZ,  AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
        (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
    ],
}


def main():
    fifo = sys.argv[1] if len(sys.argv) > 1 else '/tmp/virtpad.cmd'
    ui = UInput(CAP, name='Microsoft X-Box 360 pad',
                vendor=0x045e, product=0x028e, version=0x0110)
    # Neutralize sticks/triggers so SDL sees a settled device.
    for ax in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY, e.ABS_Z, e.ABS_RZ,
               e.ABS_HAT0X, e.ABS_HAT0Y):
        ui.write(e.EV_ABS, ax, 0)
    ui.syn()
    node = ensure_dev_node()
    sys.stderr.write(f'[virtpad] created Xbox 360 pad (node={node}); commands <- {fifo}\n')
    sys.stderr.flush()

    if not os.path.exists(fifo):
        os.mkfifo(fifo)

    # The game polls controller state at a modest rate, so a too-short press is
    # missed. Default holds are generous enough to register reliably.
    def tap(btn, secs):
        ui.write(e.EV_KEY, btn, 1); ui.syn()
        time.sleep(secs)
        ui.write(e.EV_KEY, btn, 0); ui.syn()

    def dpad(direction, secs=0.35):
        x = {'left': -1, 'right': 1}.get(direction, 0)
        y = {'up': -1, 'down': 1}.get(direction, 0)
        ui.write(e.EV_ABS, e.ABS_HAT0X, x)
        ui.write(e.EV_ABS, e.ABS_HAT0Y, y)
        ui.syn()
        if direction != 'center':
            time.sleep(secs)
            ui.write(e.EV_ABS, e.ABS_HAT0X, 0)
            ui.write(e.EV_ABS, e.ABS_HAT0Y, 0)
            ui.syn()

    # Re-open the FIFO in a loop (each writer close sends EOF).
    while True:
        with open(fifo) as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                cmd = parts[0].lower()
                try:
                    if cmd == 'press':
                        tap(BTN[parts[1].upper()], float(parts[2]) if len(parts) > 2 else 0.2)
                    elif cmd == 'down':
                        ui.write(e.EV_KEY, BTN[parts[1].upper()], 1); ui.syn()
                    elif cmd == 'up':
                        ui.write(e.EV_KEY, BTN[parts[1].upper()], 0); ui.syn()
                    elif cmd == 'dpad':
                        dpad(parts[1].lower())
                    elif cmd == 'stick':
                        ax = (e.ABS_X, e.ABS_Y) if parts[1].lower() == 'l' else (e.ABS_RX, e.ABS_RY)
                        ui.write(e.EV_ABS, ax[0], int(parts[2]))
                        ui.write(e.EV_ABS, ax[1], int(parts[3])); ui.syn()
                    elif cmd == 'trig':
                        ax = e.ABS_Z if parts[1].lower() == 'l' else e.ABS_RZ
                        ui.write(e.EV_ABS, ax, int(parts[2])); ui.syn()
                    elif cmd == 'sleep':
                        time.sleep(float(parts[1]))
                    elif cmd == 'quit':
                        ui.close(); return
                    sys.stderr.write(f'[virtpad] {line.strip()}\n'); sys.stderr.flush()
                except (KeyError, IndexError, ValueError) as ex:
                    sys.stderr.write(f'[virtpad] bad command {line.strip()!r}: {ex}\n')


if __name__ == '__main__':
    main()
