#!/usr/bin/env bash
# VN Stock ML Lab — macOS/Linux launcher
# Double-click (Terminal) hoac: bash start.sh
# ──────────────────────────────────────────────────────────────────────────────
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/server.log"
VENV="$SCRIPT_DIR/venv"
BACKEND="$SCRIPT_DIR/backend"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
SERVER_PID=""

# ── Gatekeeper: xoa co quarantine de double-click hoat dong binh thuong ──────
xattr -dr com.apple.quarantine "$SCRIPT_DIR" 2>/dev/null || true
chmod +x "$0" 2>/dev/null || true

echo ""
echo "  +--------------------------------------------------+"
echo "  |         VN Stock ML Lab  --  Khoi dong           |"
echo "  +--------------------------------------------------+"
echo ""

# ── Helpers ───────────────────────────────────────────────────────────────────
port_in_use() { lsof -ti:"$1" > /dev/null 2>&1; }

_python_ok() {
    local bin="$1"
    command -v "$bin" &>/dev/null || return 1
    "$bin" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null
}

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        echo ""
        echo "   -->  Dang dung server..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        echo "  [OK]  Da dung server."
        echo ""
    fi
}
trap cleanup EXIT INT TERM

# ── Buoc 1: Tim Python 3.10+ ──────────────────────────────────────────────────
echo "  [1/4] Tim Python 3.10+..."
echo "  ------------------------------------------------"

PYTHON=""

# 1a. Cac lenh co san trong PATH
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if _python_ok "$candidate"; then
        PYTHON="$candidate"
        break
    fi
done

# 1b. Duong dan Homebrew (Apple Silicon va Intel)
if [ -z "$PYTHON" ]; then
    for p in \
        /opt/homebrew/opt/python@3.13/bin/python3.13 \
        /opt/homebrew/opt/python@3.12/bin/python3.12 \
        /opt/homebrew/opt/python@3.11/bin/python3.11 \
        /opt/homebrew/opt/python@3.10/bin/python3.10 \
        /opt/homebrew/bin/python3 \
        /usr/local/opt/python@3.13/bin/python3.13 \
        /usr/local/opt/python@3.12/bin/python3.12 \
        /usr/local/opt/python@3.11/bin/python3.11 \
        /usr/local/opt/python@3.10/bin/python3.10 \
        /usr/local/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
        /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 \
        /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
    do
        if _python_ok "$p"; then
            PYTHON="$p"
            break
        fi
    done
fi

# 1c. Tu dong cai qua Homebrew neu khong tim thay
if [ -z "$PYTHON" ]; then
    echo "   [!]  Khong tim thay Python 3.10+ -- thu cai tu dong..."
    if command -v brew &>/dev/null; then
        echo "   -->  Homebrew tim thay. Dang cai Python 3.12..."
        brew install python@3.12 2>&1 | grep -E "(Already installed|Pouring|Installing|Error|Warning)" || true
        brew link --overwrite python@3.12 2>/dev/null || true
        for p in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
            if _python_ok "$p"; then PYTHON="$p"; break; fi
        done
        [ -z "$PYTHON" ] && _python_ok python3.12 && PYTHON="python3.12" || true
        [ -z "$PYTHON" ] && _python_ok python3    && PYTHON="python3"    || true
        CERT_CMD="/Applications/Python 3.12/Install Certificates.command"
        [ -f "$CERT_CMD" ] && bash "$CERT_CMD" > /dev/null 2>&1 || true
    else
        echo "   -->  Homebrew khong co -- tai Python 3.12 tu python.org..."
        PY_PKG_URL="https://www.python.org/ftp/python/3.12.9/python-3.12.9-macos11.pkg"
        PY_PKG_TMP="/tmp/python_install.pkg"
        if curl -fL --max-time 300 --progress-bar "$PY_PKG_URL" -o "$PY_PKG_TMP" 2>&1; then
            echo "   -->  Dang cai (co the yeu cau mat khau Mac)..."
            sudo installer -pkg "$PY_PKG_TMP" -target / 2>&1 | grep -v "^$" || true
            rm -f "$PY_PKG_TMP"
            CERT_CMD="/Applications/Python 3.12/Install Certificates.command"
            [ -f "$CERT_CMD" ] && bash "$CERT_CMD" > /dev/null 2>&1 || true
            for p in /usr/local/bin/python3.12 \
                     /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12; do
                if _python_ok "$p"; then PYTHON="$p"; break; fi
            done
            [ -z "$PYTHON" ] && _python_ok python3.12 && PYTHON="python3.12" || true
        else
            rm -f "$PY_PKG_TMP"
        fi
    fi
fi

if [ -z "$PYTHON" ]; then
    echo ""
    echo " [LOI]  Khong tim thay va khong the tu dong cai Python 3.10+."
    echo ""
    echo "  CACH CAI PYTHON:"
    echo "    Cach 1: Homebrew  →  brew install python@3.12"
    echo "    Cach 2: python.org →  https://www.python.org/downloads/"
    echo "            Tai 'Python 3.12.x macOS installer' roi bam Continue → Install"
    echo ""
    open "https://www.python.org/downloads/" 2>/dev/null || true
    echo "  Nhan Enter de dong..."
    read -r || true
    exit 1
fi

PY_VER="$("$PYTHON" --version 2>&1)"
echo "  [OK]  $PY_VER"
echo ""

# ── Buoc 2: Tao / kiem tra moi truong ao ─────────────────────────────────────
echo "  [2/4] Tao / kiem tra moi truong ao..."
echo "  ------------------------------------------------"

if [ -f "$VENV/bin/python" ]; then
    echo "  [OK]  Da co san."
elif [ -d "$VENV" ]; then
    echo "   [!]  Moi truong ao bi hong -- dang xoa de tao lai..."
    rm -rf "$VENV"
    echo "   -->  Dang tao (chi lam mot lan)..."
    if ! "$PYTHON" -m venv "$VENV" 2>/dev/null; then
        echo "   -->  venv that bai, thu cai virtualenv..."
        "$PYTHON" -m pip install --quiet virtualenv
        "$PYTHON" -m virtualenv "$VENV"
    fi
    echo "  [OK]  Da tao xong."
else
    echo "   -->  Dang tao (chi lam mot lan)..."
    if ! "$PYTHON" -m venv "$VENV" 2>/dev/null; then
        echo "   -->  venv that bai, thu cai virtualenv..."
        "$PYTHON" -m pip install --quiet virtualenv
        "$PYTHON" -m virtualenv "$VENV"
    fi
    echo "  [OK]  Da tao xong."
fi

if [ ! -f "$VENV/bin/python" ]; then
    echo ""
    echo " [LOI]  Khong the tao moi truong ao tai: $VENV"
    echo "   -->  Kiem tra o dia con trong (can >= 500 MB)."
    echo "   -->  Thu xoa thu muc venv/ roi chay lai."
    echo ""
    echo "  Nhan Enter de dong..."
    read -r || true
    exit 1
fi

PYTHON="$VENV/bin/python"
VENV_PIP="$VENV/bin/pip"
VENV_UVICORN="$VENV/bin/uvicorn"
echo ""

# ── Buoc 3: Cai dat / kiem tra thu vien ──────────────────────────────────────
echo "  [3/4] Cai dat / kiem tra thu vien..."
echo "  ------------------------------------------------"

if "$PYTHON" -c "import fastapi, uvicorn, sklearn, pandas, arch" 2>/dev/null; then
    echo "  [OK]  Da co san."
else
    echo "   -->  Lan dau cai dat: khoang 3-5 phut, vui long KHONG TAT cua so nay..."
    "$VENV_PIP" install --upgrade pip --quiet > /dev/null 2>&1
    if ! "$VENV_PIP" install -r "$REQUIREMENTS" -q 2>&1; then
        echo ""
        echo " [LOI]  Cai dat thu vien that bai. Chi tiet loi:"
        echo ""
        "$VENV_PIP" install -r "$REQUIREMENTS"
        echo ""
        echo "   -->  Kiem tra: ket noi internet? o dia con trong?"
        echo "   -->  Thu xoa thu muc venv/ roi chay lai."
        echo ""
        echo "  Nhan Enter de dong..."
        read -r || true
        exit 1
    fi
    echo "  [OK]  Cai dat xong."
fi
echo ""

# ── Buoc 4: Tim cong va khoi dong server ─────────────────────────────────────
echo "  [4/4] Tim cong va khoi dong server..."
echo "  ------------------------------------------------"

PORT=""
for p in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009; do
    if ! port_in_use "$p"; then
        PORT="$p"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo ""
    echo " [LOI]  Khong tim duoc cong trong (8000-8009 deu ban)."
    echo "  Nhan Enter de dong..."
    read -r || true
    exit 1
fi

[ "$PORT" != "8000" ] && echo "   [!]  Cong 8000 dang ban -- dung cong $PORT."

echo "   -->  Dang khoi dong server..."
( cd "$BACKEND" && exec "$PYTHON" -m uvicorn main:app \
    --host 127.0.0.1 --port "$PORT" \
    --log-level warning --no-access-log \
) > "$LOG" 2>&1 &
SERVER_PID="$!"

# Cho server san sang (kiem tra port, toi da 30 giay)
printf "  [cho server khoi dong"
READY=0
for i in $(seq 1 30); do
    sleep 1
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        printf "] CRASH!\n"
        READY=0
        break
    fi
    if port_in_use "$PORT"; then
        printf "] san sang!\n"
        READY=1
        break
    fi
    printf "."
    if [ "$i" -eq 30 ]; then
        printf "] HET THOI GIAN!\n"
    fi
done

if [ "$READY" -ne 1 ]; then
    echo ""
    echo " [LOI]  Server khong khoi dong duoc."
    if [ -f "$LOG" ] && [ -s "$LOG" ]; then
        echo ""
        echo "  --- Chi tiet loi server (server.log) ---"
        tail -30 "$LOG" | while IFS= read -r line; do echo "  $line"; done
        echo "  ----------------------------------------"
    fi
    echo ""
    echo "   -->  Thu xoa thu muc venv/ roi chay lai."
    echo ""
    echo "  Nhan Enter de dong..."
    read -r || true
    exit 1
fi

URL="http://127.0.0.1:$PORT"
echo ""
echo "  +--------------------------------------------------+"
echo "  |  Dia chi :  $URL"
echo "  |  !! GIU CUA SO NAY MO de server tiep tuc chay!! |"
echo "  |  Nhan Ctrl+C trong cua so nay de dung server.   |"
echo "  +--------------------------------------------------+"
echo ""

echo "   -->  Dang mo trinh duyet..."
open "$URL" 2>/dev/null || true

# Giu cua so mo, cho den khi nguoi dung nhan Ctrl+C
wait "$SERVER_PID" 2>/dev/null || true
