import pytest
import sys
import platform
from unittest.mock import patch

if platform.system() == "Windows":
    from armonik_cli.core.input import get_key  # Replace `your_module` with the actual module name
else:
    from armonik_cli.core.input import (
        get_key,
    )  # Replace `your_module` with the actual module name


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific tests")
def test_get_key_windows_blocking():
    """Test `get_key` on Windows in blocking mode"""
    with patch("msvcrt.getch", return_value=b"A"):
        key = get_key(blocking=True)
        assert key == "A"


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific tests")
def test_get_key_windows_nonblocking():
    """Test `get_key` on Windows in non-blocking mode"""
    with patch("msvcrt.kbhit", return_value=True), patch("msvcrt.getch", return_value=b"B"):
        key = get_key(blocking=False)
        assert key == "B"


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific tests")
def test_get_key_windows_nonblocking_no_key():
    """Test `get_key` on Windows in non-blocking mode when no key is pressed"""
    with patch("msvcrt.kbhit", return_value=False):
        key = get_key(blocking=False)
        assert key == ""  # No key was pressed


@pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific tests")
def test_get_key_unix_blocking():
    """Test `get_key` on Unix in blocking mode"""
    with patch("os.read", return_value=b"C"), patch("sys.stdin.fileno", return_value=0), patch(
        "termios.tcgetattr"
    ), patch("tty.setcbreak"), patch("termios.tcsetattr"):
        key = get_key(blocking=True)
        assert key == "C"


@pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific tests")
def test_get_key_unix_nonblocking_key_pressed():
    """Test `get_key` on Unix in non-blocking mode when a key is pressed"""
    with patch("select.select", return_value=([sys.stdin], [], [])), patch(
        "os.read", return_value=b"D"
    ), patch("sys.stdin.fileno", return_value=0), patch("termios.tcgetattr"), patch(
        "tty.setcbreak"
    ), patch("termios.tcsetattr"):
        key = get_key(blocking=False)
        assert key == "D"


@pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific tests")
def test_get_key_unix_nonblocking_no_key():
    """Test `get_key` on Unix in non-blocking mode when no key is pressed"""
    with patch("select.select", return_value=([], [], [])), patch(
        "sys.stdin.fileno", return_value=0
    ), patch("termios.tcgetattr"), patch("tty.setcbreak"), patch("termios.tcsetattr"):
        key = get_key(blocking=False)
        assert key == ""  # No key was pressed


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific tests")
def test_get_key_windows_ctrl_c():
    """Test `get_key` on Windows catching Ctrl+C"""
    with patch("msvcrt.getch", side_effect=KeyboardInterrupt):
        key = get_key(blocking=True, catch=True)
        assert key == "\x03"  # Ctrl+C


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific tests")
def test_get_key_windows_keyboard_interrupt():
    """Test `get_key` on Windows raising KeyboardInterrupt"""
    with patch("msvcrt.getch", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            get_key(blocking=True, catch=False)
