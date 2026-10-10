import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path
import cli
from test_core import site


def test_real_tty_single_key_navigation_without_enter(site):
    assert hasattr(cli, 'read_terminal_command'), 'Raw terminal shortcut navigation is missing'
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, str(Path(__file__).parents[1] / 'we.py'), '--root', str(site), 'shell', '--member', 'murmuur'], stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    transcript = bytearray()
    def until(text):
        deadline = time.monotonic() + 8
        while text.encode() not in transcript:
            assert time.monotonic() < deadline, transcript.decode(errors='replace')[-2000:]
            if select.select([master], [], [], .1)[0]:
                transcript.extend(os.read(master, 65536))
    try:
        until('single key')
        os.write(master, b'g')
        until('Field of view.')
        os.write(master, b'?')
        until('You already know how.')
        os.write(master, b'q')
        deadline = time.monotonic() + 8
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    transcript.extend(os.read(master, 65536))
                except OSError:
                    break
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.terminate(); process.wait(timeout=5)
        os.close(master)
