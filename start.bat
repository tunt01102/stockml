@echo off
chcp 65001 >nul 2>&1
title VN Stock ML Lab
cd /d "%~dp0"

echo.
echo  +--------------------------------------------------+
echo  ^|         VN Stock ML Lab  --  Launcher            ^|
echo  +--------------------------------------------------+
echo.

:: Try "py" launcher (recommended Python for Windows installer)
where py >nul 2>&1
if %errorlevel% == 0 (
    py -3 start.py
    goto :done
)

:: Try "python"
where python >nul 2>&1
if %errorlevel% == 0 (
    python start.py
    goto :done
)

:: Try "python3"
where python3 >nul 2>&1
if %errorlevel% == 0 (
    python3 start.py
    goto :done
)

:: Python not found
echo.
echo  [LOI] Khong tim thay Python 3.10+.
echo.
echo  Huong dan cai dat:
echo    1. Truy cap: https://www.python.org/downloads/
echo    2. Tai phien ban moi nhat (3.10 tro len)
echo    3. Khi cai dat, CHON "Add Python to PATH"
echo    4. Mo lai cua so nay sau khi cai xong
echo.

:done
pause
