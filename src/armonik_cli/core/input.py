import sys
import platform
import select
import os

KEY_MAP_UNIX = {
    "UP": "\x1b[A",
    "DOWN": "\x1b[B",
    "RIGHT": "\x1b[C",
    "LEFT": "\x1b[D",
    "ESCAPE": "\x1b",
}

if platform.system() == "Windows":
    import msvcrt

    def get_key(blocking=True, timeout=0.1, catch_ctrlc=False):
        """Reads a single key press in Windows."""
        if not blocking:
            key = msvcrt.getch() if msvcrt.kbhit() else b""
        else:
            try:
                key1 = msvcrt.getch()
                # If it's a special character prefix:
                if key1 in (b"\x00", b"\xe0"):
                    key2 = msvcrt.getch()
                    if key2 == b"H":
                        return "UP"
                    elif key2 == b"P":
                        return "DOWN"
                    elif key2 == b"M":
                        return "RIGHT"
                    elif key2 == b"K":
                        return "LEFT"

                # Otherwise it's a normal key:
                return key1.decode(errors="ignore")
            except KeyboardInterrupt:
                if not catch_ctrlc:
                    raise
                key = b"\x03"  # Handle Ctrl+C interruption

        key = key.decode(errors="ignore")  # Decode bytes to string safely
        return key

else:
    import tty
    import termios

    class RawInput:
        def __enter__(self):
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(blocking=True, timeout=0.1, catch_ctrlc=False):
        """Reads a single key press from stdin with optional timeout."""
        with RawInput():
            ev, _, _ = select.select([sys.stdin], [], [], None if blocking else timeout)
            if not ev:
                return ""  # No key within the timeout

            # Read up to, say, 4 bytes
            # (enough to capture escape + [ + some letter, or smaller sequences)
            data = os.read(sys.stdin.fileno(), 4).decode(errors="ignore")

            # Now parse what was read:
            # If it starts with \x1b but has more characters, see if it's an arrow
            if data.startswith("\x1b"):
                # Could be an arrow, function key, or just ESC
                if data.startswith("\x1b[A"):
                    return "UP"
                elif data.startswith("\x1b[B"):
                    return "DOWN"
                elif data.startswith("\x1b[C"):
                    return "RIGHT"
                elif data.startswith("\x1b[D"):
                    return "LEFT"
                else:
                    # The user hit just ESC, or some other escape sequence
                    return "ESCAPE"

            # For “normal” printable keys, it’ll just be data[0]
            return data[0]
