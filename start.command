#!/bin/bash
# VN Stock ML Lab -- macOS launcher
# Double-click file nay de chay ung dung.
#
# Lan dau su dung (neu bi macOS block):
#   Right-click -> Open -> Open

# Move to the folder containing this script
cd "$(dirname "$0")"

# Find python3 or python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    osascript -e 'display alert "Thieu Python 3.10+" message "Tai ve tai https://python.org va cai dat truoc khi chay lai." as critical'
    echo ""
    echo "  [LOI] Khong tim thay Python."
    echo "  Tai: https://www.python.org/downloads/"
    echo ""
    read -p "  Nhan Enter de dong..."
    exit 1
fi

# Check minimum version (3.10)
PY_VER=$($PYTHON -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
if [ "$PY_VER" != "True" ]; then
    osascript -e 'display alert "Python qua cu" message "Can Python 3.10+. Tai ve tai https://python.org" as critical'
    echo ""
    echo "  [LOI] Python hien tai chua du phien ban (can >= 3.10)."
    echo "  Tai: https://www.python.org/downloads/"
    echo ""
    read -p "  Nhan Enter de dong..."
    exit 1
fi

$PYTHON start.py
