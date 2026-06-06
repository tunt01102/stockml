#!/usr/bin/env python3
"""
start.py -- VN Stock ML Lab one-click launcher
Cross-platform: macOS va Windows.
Chi dung Python standard library truoc khi venv duoc tao.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 output (Windows compatibility)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent       # stockml/
VENV         = ROOT / "venv"
WIN          = sys.platform == "win32"

VENV_PYTHON  = VENV / ("Scripts/python.exe"  if WIN else "bin/python3")
VENV_PIP     = VENV / ("Scripts/pip.exe"     if WIN else "bin/pip")
VENV_UVICORN = VENV / ("Scripts/uvicorn.exe" if WIN else "bin/uvicorn")

BACKEND      = ROOT / "backend"
REQUIREMENTS = ROOT / "requirements.txt"
SCRIPT       = Path(__file__).resolve()

# ── Print helpers ──────────────────────────────────────────────────────────
def _p(icon: str, msg: str) -> None:
    print(f"  {icon}  {msg}", flush=True)

def ok(msg: str)  -> None: _p("[OK]", msg)
def inf(msg: str) -> None: _p("-->", msg)
def warn(msg: str)-> None: _p("[!]", msg)
def err(msg: str) -> None: _p("[LOI]", msg); print()


# ── Step 1: Banner + version check ────────────────────────────────────────
def banner() -> None:
    v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print()
    print("  +--------------------------------------------------+")
    print("  |         VN Stock ML Lab  --  Launcher            |")
    print(f"  |  Python {v:<41}|")
    print("  +--------------------------------------------------+")
    print()


def check_python() -> None:
    if sys.version_info < (3, 10):
        err(
            f"Python {sys.version_info.major}.{sys.version_info.minor} "
            "chua du (can >= 3.10)."
        )
        inf("Tai ve tai: https://www.python.org/downloads/")
        sys.exit(1)
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


# ── Step 2: chmod start.command (macOS only) ───────────────────────────────
def ensure_command_executable() -> None:
    """Ensure start.command is executable so macOS can double-click it."""
    if sys.platform != "darwin":
        return
    cmd_file = ROOT / "start.command"
    if cmd_file.exists():
        import stat
        cmd_file.chmod(
            cmd_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )


# ── Step 3: Venv bootstrap ─────────────────────────────────────────────────
def bootstrap_venv() -> None:
    """
    If not already inside venv:
      - Create venv if missing
      - Re-launch this script with the venv Python
    Uses env var '_STOCKML_VENV=1' as guard to prevent infinite loop.
    """
    if os.environ.get("_STOCKML_VENV"):
        return  # already inside venv

    if not VENV.exists():
        inf("Tao moi truong ao (chi mot lan, ~10 giay)...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "venv", str(VENV)],
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            err("Khong the tao moi truong ao.")
            inf("Thu chay: python -m venv venv")
            sys.exit(1)
        ok("Moi truong ao da duoc tao.")
    else:
        ok("Moi truong ao da co san.")

    inf("Khoi dong lai trong moi truong ao...")
    new_env = {**os.environ, "_STOCKML_VENV": "1"}

    if WIN:
        result = subprocess.run([str(VENV_PYTHON), str(SCRIPT)], env=new_env)
        sys.exit(result.returncode)
    else:
        # os.execve replaces current process (no double banner)
        os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPT)], new_env)


# ── Step 4: Install requirements ──────────────────────────────────────────
def install_requirements() -> None:
    inf("Kiem tra va cai thu vien (lan dau co the mat vai phut)...")
    try:
        subprocess.check_call(
            [str(VENV_PIP), "install", "-r", str(REQUIREMENTS), "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # Re-run with visible output so user can see what went wrong
        print()
        subprocess.run(
            [str(VENV_PIP), "install", "-r", str(REQUIREMENTS)],
        )
        err("Cai thu vien that bai (xem loi phia tren).")
        inf("Kiem tra ket noi internet va thu lai.")
        sys.exit(1)
    ok("Tat ca thu vien san sang.")


# ── Step 5: Find free port ─────────────────────────────────────────────────
def find_free_port(start: int = 8000, n: int = 10) -> int:
    for port in range(start, start + n):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Khong tim duoc port trong ({start}-{start + n - 1}).")


# ── Step 6: Start uvicorn ──────────────────────────────────────────────────
def start_server(port: int) -> subprocess.Popen:
    cmd = [
        str(VENV_UVICORN), "main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--no-access-log",
    ]
    return subprocess.Popen(cmd, cwd=str(BACKEND))


# ── Step 7: Poll until server is ready ────────────────────────────────────
def wait_for_server(port: int, timeout: int = 60) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    print("  -->  Cho server khoi dong", end="", flush=True)
    for _ in range(timeout):
        try:
            urllib.request.urlopen(url, timeout=1)
            print(" san sang!", flush=True)
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)
    print()
    return False


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    # Only print banner & check Python before entering venv (avoid double print)
    if not os.environ.get("_STOCKML_VENV"):
        banner()
        check_python()
        ensure_command_executable()

    bootstrap_venv()
    # ↑ may os.execve / sys.exit — code below only runs inside venv

    install_requirements()

    port = find_free_port()
    if port != 8000:
        warn(f"Cong 8000 dang ban, dung cong {port}.")

    inf(f"Khoi dong server tren cong {port}...")
    proc = start_server(port)

    if not wait_for_server(port):
        err("Server khong phan hoi sau 60 giay.")
        proc.terminate()
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    ok(f"Server san sang: {url}")

    if sys.platform == "darwin":
        print()
        inf("macOS: Neu bi block lan dau -> right-click start.command -> Open")

    inf("Dang mo trinh duyet...")
    webbrowser.open(url)

    print()
    print("  " + "-" * 48)
    print("  Ung dung dang chay. Nhan Ctrl+C de dung.")
    print("  " + "-" * 48)
    print()

    try:
        proc.wait()
    except KeyboardInterrupt:
        print()
        inf("Dang dung server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        ok("Da dung server.")
        print()


if __name__ == "__main__":
    main()
