import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path
from test_explorer import source


def test_directory_terminal_real_keys_arrows_and_parent_navigation(source,tmp_path):
    master,slave=pty.openpty()
    process=subprocess.Popen([sys.executable,str(Path(__file__).parents[1]/'explorer.py'),'--source',str(source),'--state',str(tmp_path/'state'),'shell','/@murmuur/'],stdin=slave,stdout=slave,stderr=slave)
    os.close(slave)
    transcript=bytearray()
    def until(marker,start=0):
        deadline=time.monotonic()+8
        while marker.encode() not in transcript[start:]:
            assert time.monotonic()<deadline,transcript.decode(errors='replace')[-1600:]
            if select.select([master],[],[],.1)[0]:transcript.extend(os.read(master,65536))
    try:
        until('single key')
        mark=len(transcript);os.write(master,b'p')
        until('ls /@murmuur/photography/',mark)
        until('single key',mark)
        mark=len(transcript);os.write(master,b'u')
        until('ls /@murmuur/',mark)
        until('single key',mark)
        mark=len(transcript);os.write(master,b'\x1b[B\x1b[B\r')
        until('ls /@murmuur/photography/',mark)
        until('single key',mark)
        os.write(master,b'q')
        deadline=time.monotonic()+8
        while process.poll() is None and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                try:transcript.extend(os.read(master,65536))
                except OSError:break
        assert process.wait(timeout=2)==0
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)
        os.close(master)
