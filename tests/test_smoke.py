"""Smoke test headless dell'intero gioco (driver video/audio "dummy")."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_smoke_headless():
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    res = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "smoke_test.py")],
                         capture_output=True, text=True, env=env, timeout=180)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "SMOKE TEST OK" in res.stdout
