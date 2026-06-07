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
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent
VENV         = ROOT / "venv"
WIN          = sys.platform == "win32"

VENV_PYTHON  = VENV / ("Scripts/python.exe"  if WIN else "bin/python3")
VENV_PIP     = VENV / ("Scripts/pip.exe"     if WIN else "bin/pip")
VENV_UVICORN = VENV / ("Scripts/uvicorn.exe" if WIN else "bin/uvicorn")

BACKEND      = ROOT / "backend"
REQUIREMENTS = ROOT / "requirements.txt"
SCRIPT       = Path(__file__).resolve()

# ── Print helpers ──────────────────────────────────────────────────────────
def _hr() -> None:
    print("  " + "-" * 48, flush=True)

def _step(n: int, title: str) -> None:
    print(f"\n  [{n}/4] {title}", flush=True)
    _hr()

def ok(msg: str)   -> None: print(f"  [OK]  {msg}", flush=True)
def inf(msg: str)  -> None: print(f"   -->  {msg}", flush=True)
def warn(msg: str) -> None: print(f"   [!]  {msg}", flush=True)
def err(msg: str)  -> None: print(f" [LOI]  {msg}", flush=True)


# ── Banner ─────────────────────────────────────────────────────────────────
def banner() -> None:
    v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print()
    print("  +--------------------------------------------------+")
    print("  |         VN Stock ML Lab  --  Khoi dong           |")
    print(f"  |  Python {v:<41}|")
    print("  +--------------------------------------------------+")
    print()


# ── Step 1: Python version check ──────────────────────────────────────────
def check_python() -> None:
    if sys.version_info < (3, 10):
        err(f"Python {sys.version_info.major}.{sys.version_info.minor} qua cu (can >= 3.10).")
        inf("Tai phien ban moi tai: https://www.python.org/downloads/")
        inf("Khi cai: CHON 'Add Python to PATH'.")
        _pause_and_exit()
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


# ── macOS: ensure start.command is executable ─────────────────────────────
def ensure_command_executable() -> None:
    if sys.platform != "darwin":
        return
    cmd_file = ROOT / "start.command"
    if cmd_file.exists():
        import stat
        cmd_file.chmod(cmd_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ── Step 2: Venv bootstrap ─────────────────────────────────────────────────
def bootstrap_venv() -> None:
    if os.environ.get("_STOCKML_VENV"):
        return  # already inside venv — steps 3-4 will run

    if not VENV.exists():
        inf("Tao moi truong ao moi (chi lam mot lan)...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "venv", str(VENV)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            err("Khong the tao moi truong ao.")
            inf("Thu chay: python -m venv venv")
            _pause_and_exit()

        if not VENV_PYTHON.exists():
            err(f"Tao venv xong nhung khong tim thay: {VENV_PYTHON}")
            err("Co the do quyen ghi bi han che hoac o dia day.")
            _pause_and_exit()

        ok("Moi truong ao da tao xong.")
    else:
        if not VENV_PYTHON.exists():
            err("Moi truong ao bi hong. Xoa thu muc 'venv' roi chay lai.")
            _pause_and_exit()
        ok("Moi truong ao co san.")

    inf("Dang chay trong moi truong ao...")
    new_env = {**os.environ, "_STOCKML_VENV": "1"}

    if WIN:
        result = subprocess.run([str(VENV_PYTHON), str(SCRIPT)], env=new_env)
        sys.exit(result.returncode)
    else:
        os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPT)], new_env)


# ── Step 3: Install requirements ──────────────────────────────────────────
def _dot_printer(stop_evt: threading.Event) -> None:
    """Print a dot every 4 sec so user knows something is happening."""
    print("  [dang cai dat", end="", flush=True)
    while not stop_evt.wait(4.0):
        print(".", end="", flush=True)


def install_requirements() -> None:
    first_time = not VENV_UVICORN.exists()

    if first_time:
        inf("Lan dau cai dat: khoang 3-5 phut, vui long KHONG TAT cua so nay...")
        stop_evt = threading.Event()
        t = threading.Thread(target=_dot_printer, args=(stop_evt,), daemon=True)
        t.start()
    else:
        inf("Kiem tra thu vien...")

    try:
        subprocess.check_call(
            [str(VENV_PIP), "install", "-r", str(REQUIREMENTS), "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if first_time:
            stop_evt.set()
            t.join(timeout=1)
            print("] xong!", flush=True)
        ok("Tat ca thu vien san sang.")

    except subprocess.CalledProcessError:
        if first_time:
            stop_evt.set()
            t.join(timeout=1)
            print("] loi!", flush=True)
        print()
        err("Cai dat thu vien that bai. Chi tiet loi:")
        print()
        subprocess.run([str(VENV_PIP), "install", "-r", str(REQUIREMENTS)])
        print()
        inf("Kiem tra: ket noi internet? o dia con trong? Xoa 'venv' roi thu lai.")
        _pause_and_exit()


# ── Step 4: Find free port ─────────────────────────────────────────────────
def find_free_port(start: int = 8000, n: int = 10) -> int:
    for port in range(start, start + n):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Khong tim duoc port trong ({start}-{start + n - 1}).")


# ── Step 4: Start uvicorn ──────────────────────────────────────────────────
def start_server(port: int) -> subprocess.Popen:
    cmd = [
        str(VENV_UVICORN), "main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--no-access-log",
    ]
    return subprocess.Popen(cmd, cwd=str(BACKEND))


# ── Step 4: Poll until server ready ───────────────────────────────────────
def wait_for_server(port: int, timeout: int = 60) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    print("  [cho server khoi dong", end="", flush=True)
    for _ in range(timeout):
        try:
            urllib.request.urlopen(url, timeout=1)
            print("] san sang!", flush=True)
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)
    print("] HET THOI GIAN!", flush=True)
    return False


# ── Utility: keep terminal open on error ──────────────────────────────────
def _pause_and_exit(code: int = 1) -> None:
    print()
    _hr()
    if WIN:
        print("  Nhan Enter de dong cua so nay...")
        try:
            input()
        except Exception:
            pass
    sys.exit(code)


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    if not os.environ.get("_STOCKML_VENV"):
        banner()
        _step(1, "Kiem tra phien ban Python")
        check_python()
        ensure_command_executable()

        _step(2, "Tao / kiem tra moi truong ao")
        bootstrap_venv()
        # ↑ os.execve (macOS) hoac subprocess.run (Windows) -> ket thuc o day
        return  # Windows: child process da chay xong va sys.exit() da goi

    # === Chay ben trong venv ===
    _step(3, "Cai dat / kiem tra thu vien")
    install_requirements()

    _step(4, "Khoi dong server")
    port = find_free_port()
    if port != 8000:
        warn(f"Cong 8000 dang ban, dung cong {port}.")

    inf(f"Dang khoi dong server...")
    proc = start_server(port)

    if not wait_for_server(port):
        err("Server khong phan hoi sau 60 giay.")
        err("Thu xoa thu muc 'venv' roi chay lai de cai lai thu vien.")
        proc.terminate()
        _pause_and_exit()

    url = f"http://127.0.0.1:{port}"

    print()
    print("  +--------------------------------------------------+")
    print(f"  |  Dia chi :  {url:<38}|")
    print("  |  De dung  :  dong cua so Terminal nay (Ctrl+C)   |")
    print("  +--------------------------------------------------+")
    print()

    inf("Dang mo trinh duyet tu dong...")
    webbrowser.open(url)

    if sys.platform == "darwin":
        warn("macOS: Neu bi canh bao bao mat -> right-click start.command -> Open")

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
