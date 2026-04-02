"""Minimal GDB Remote Serial Protocol client for RPCS3's stub.

RPCS3's GDB stub pauses emulation when it receives a break (\x03).
After inspecting, send 'c' (continue) to resume. The RPCS3 pause
overlay ("Press and hold START to resume") may appear — send a
START button hold via xdotool after resuming to dismiss it.

Usage:
    from gdb_client import GDBClient
    with GDBClient("127.0.0.1", 2345) as gdb:
        gdb.pause()
        flags = gdb.read_u32(0x01929e14)
        gdb.resume()
"""

import socket
import time


class GDBClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 2345, timeout: float = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.noack = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        # Drain any initial data
        self._drain()
        # Try no-ack mode
        resp = self._send_cmd("QStartNoAckMode")
        if resp == "OK":
            self.noack = True

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _drain(self):
        """Read and discard any pending data."""
        self.sock.setblocking(False)
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
        except (OSError, BlockingIOError):
            pass
        self.sock.setblocking(True)
        self.sock.settimeout(self.timeout)

    def _send_raw(self, data: bytes):
        self.sock.sendall(data)

    def _recv_packet(self, timeout: float = None) -> str:
        """Receive one GDB RSP packet, return payload string."""
        if timeout is None:
            timeout = self.timeout
        self.sock.settimeout(timeout)

        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                # Look for complete $payload#XX packet
                text = buf.decode(errors="replace")
                if "$" in text:
                    start = text.index("$")
                    rest = text[start + 1 :]
                    if "#" in rest:
                        hash_pos = rest.index("#")
                        if len(rest) > hash_pos + 2:
                            payload = rest[:hash_pos]
                            # Send ack if not in no-ack mode
                            if not self.noack:
                                self._send_raw(b"+")
                            return payload
            except TimeoutError:
                break

        return ""

    def _send_cmd(self, cmd: str) -> str:
        """Send command, receive response."""
        checksum = sum(ord(c) for c in cmd) & 0xFF
        packet = f"${cmd}#{checksum:02x}".encode()
        self._send_raw(packet)
        return self._recv_packet()

    def pause(self) -> str:
        """Send break to pause emulation. Returns stop reason."""
        self._send_raw(b"\x03")
        # Wait for stop reply
        time.sleep(0.3)
        return self._recv_packet(timeout=3)

    def resume(self):
        """Send continue to resume emulation."""
        # Don't wait for response — 'c' only replies when target stops again
        checksum = sum(ord(c) for c in "c") & 0xFF
        self._send_raw(f"$c#{checksum:02x}".encode())
        time.sleep(0.2)
        self._drain()

    def read_memory(self, addr: int, length: int) -> bytes:
        """Read memory. Returns raw bytes."""
        resp = self._send_cmd(f"m{addr:x},{length}")
        if resp and not resp.startswith("E"):
            try:
                return bytes.fromhex(resp)
            except ValueError:
                pass
        return b""

    def read_u32(self, addr: int) -> int:
        """Read a big-endian 32-bit value."""
        data = self.read_memory(addr, 4)
        if len(data) == 4:
            return int.from_bytes(data, "big")
        return 0

    def get_thread_list(self) -> list[str]:
        """Get list of thread IDs."""
        threads = []
        resp = self._send_cmd("qfThreadInfo")
        while resp.startswith("m"):
            threads.extend(t.strip() for t in resp[1:].split(",") if t.strip())
            resp = self._send_cmd("qsThreadInfo")
        return threads

    def select_thread(self, tid: str):
        """Select thread for register reads."""
        self._send_cmd(f"Hg{tid}")

    def read_register(self, regnum: int) -> int:
        """Read a single register by number. Returns value."""
        resp = self._send_cmd(f"p{regnum:x}")
        if resp and not resp.startswith("E"):
            try:
                return int(resp, 16)
            except ValueError:
                pass
        return 0

    def get_pc(self) -> int:
        """Read PC (NIP) of current thread. PPC64 register 64."""
        return self.read_register(64)

    def get_lr(self) -> int:
        """Read LR of current thread. PPC64 register 65."""
        return self.read_register(65)

    def inspect_all_threads(self) -> list[dict]:
        """Get PC and LR for all threads."""
        results = []
        threads = self.get_thread_list()
        for tid in threads:
            self.select_thread(tid)
            pc = self.get_pc()
            lr = self.get_lr()
            results.append({"tid": tid, "pc": pc, "lr": lr})
        return results
