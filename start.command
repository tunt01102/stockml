#!/bin/bash
# ============================================================
# VN Stock ML Lab -- macOS launcher
# Double-click file nay de chay ung dung.
#
# LAN DAU CHAY (macOS co the canh bao bao mat):
#   1. Right-click vao file nay
#   2. Chon "Open" (khong phai double-click)
#   3. Click "Open" trong hop thoai canh bao
#   4. Tu lan sau co the double-click binh thuong
# ============================================================

# Move to the folder containing this script
cd "$(dirname "$0")"

# Remove macOS quarantine flag so double-click works after first open
xattr -dr com.apple.quarantine . 2>/dev/null

# Make sure this script stays executable
chmod +x "$0" 2>/dev/null

echo ""
echo "  +--------------------------------------------------+"
echo "  |         VN Stock ML Lab  --  Khoi dong           |"
echo "  +--------------------------------------------------+"
echo ""

# ── Find Python 3.10+ ─────────────────────────────────────────────────────
PYTHON=""

# 1. python3 (standard on macOS with Xcode Command Line Tools or Homebrew)
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
    if [ "$PY_VER" = "True" ]; then
        PYTHON=python3
    fi
fi

# 2. python (some setups)
if [ -z "$PYTHON" ] && command -v python &>/dev/null; then
    PY_VER=$(python -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
    if [ "$PY_VER" = "True" ]; then
        PYTHON=python
    fi
fi

# 3. Homebrew Python (common install location on Apple Silicon and Intel)
if [ -z "$PYTHON" ]; then
    for BREW_PY in \
        /opt/homebrew/bin/python3 \
        /usr/local/bin/python3 \
        /opt/homebrew/opt/python@3.12/bin/python3.12 \
        /opt/homebrew/opt/python@3.11/bin/python3.11 \
        /opt/homebrew/opt/python@3.10/bin/python3.10 \
        /usr/local/opt/python@3.12/bin/python3.12 \
        /usr/local/opt/python@3.11/bin/python3.11 \
        /usr/local/opt/python@3.10/bin/python3.10
    do
        if [ -x "$BREW_PY" ]; then
            PY_VER=$("$BREW_PY" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
            if [ "$PY_VER" = "True" ]; then
                PYTHON="$BREW_PY"
                break
            fi
        fi
    done
fi

# ── Python not found ──────────────────────────────────────────────────────
if [ -z "$PYTHON" ]; then
    echo ""
    echo "  [LOI] Khong tim thay Python 3.10 tro len."
    echo ""
    echo "  CACH CAI PYTHON:"
    echo ""
    echo "  Cach 1 (don gian nhat):"
    echo "    1. Vao: https://www.python.org/downloads/"
    echo "    2. Click 'Download Python 3.12.x'"
    echo "    3. Mo file .pkg vua tai, bam Continue -> Install"
    echo "    4. Sau khi cai xong, dong va mo lai Terminal nay"
    echo ""
    echo "  Cach 2 (neu da co Homebrew):"
    echo "    brew install python@3.12"
    echo ""

    # Show dialog on macOS
    osascript -e 'display alert "Thieu Python 3.10+" message "Can cai Python 3.10 tro len.\n\nVao https://www.python.org/downloads/ tai Python 3.12.\n\nChay lai start.command sau khi cai xong." as critical buttons {"Mo trang tai"} default button 1' 2>/dev/null
    open "https://www.python.org/downloads/" 2>/dev/null

    echo ""
    read -p "  Nhan Enter de dong..."
    exit 1
fi

# ── Check minimum version ─────────────────────────────────────────────────
PY_DISPLAY=$($PYTHON --version 2>&1)
echo "  Python: $PY_DISPLAY"
echo "  OK -- Dang khoi dong..."
echo ""

# ── Run start.py ──────────────────────────────────────────────────────────
$PYTHON start.py
EXIT_CODE=$?

# Keep terminal open if there was an error
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "  --------------------------------------------------"
    echo "  Ung dung thoat voi loi (code: $EXIT_CODE)."
    echo "  Doc thong bao phia tren de biet nguyen nhan."
    echo "  --------------------------------------------------"
    echo ""
    read -p "  Nhan Enter de dong..."
fi
