@echo off
chcp 65001 >nul 2>&1
title VN Stock ML Lab
cd /d "%~dp0"

echo.
echo  +--------------------------------------------------+
echo  ^|         VN Stock ML Lab  --  Launcher            ^|
echo  +--------------------------------------------------+
echo.

:: ── 1. py.exe (Python Launcher for Windows) ────────────────────────────────
::    Included with the official Python installer. Most reliable on Windows.
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 start.py
    goto :done
)

:: ── 2. python / python3 in PATH ────────────────────────────────────────────
::    Windows 10/11 has a fake "python.exe" Store alias that passes `where`
::    but outputs an install prompt instead of "Python 3.x.x".
::    We detect this by piping --version output through findstr:
::    real Python prints "Python 3.x.x"; the Store stub does NOT.
python --version 2>&1 | findstr /b /c:"Python 3" >nul 2>&1
if not errorlevel 1 (
    python start.py
    goto :done
)

python3 --version 2>&1 | findstr /b /c:"Python 3" >nul 2>&1
if not errorlevel 1 (
    python3 start.py
    goto :done
)

:: ── 3. Hardcoded user-install paths (default for official installer) ────────
call :try "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"

:: ── 4. Hardcoded system-install paths ──────────────────────────────────────
call :try "%PROGRAMFILES%\Python313\python.exe"
call :try "%PROGRAMFILES%\Python312\python.exe"
call :try "%PROGRAMFILES%\Python311\python.exe"
call :try "%PROGRAMFILES%\Python310\python.exe"

:: ── Python not found ────────────────────────────────────────────────────────
echo.
echo  [LOI] Khong tim thay Python 3.10 tro len.
echo.
echo  NGUYEN NHAN PHO BIEN:
echo    1. Chua cai Python
echo    2. Cai Python nhung quen chon "Add Python to PATH"
echo    3. Windows Store alias dang che khuat Python that (loi tren)
echo.
echo  CACH SUA:
echo    Buoc 1: Vao https://www.python.org/downloads/
echo            Tai Python 3.12 (hoac moi hon), chay bo cai dat
echo            QUAN TRONG: tick vao o "Add Python to PATH" truoc khi Next
echo.
echo    Buoc 2: Neu da cai Python nhung van bi loi tren:
echo            Mo Settings ^> Apps ^> Advanced app settings
echo                       ^> App execution aliases
echo            Tim dong "python.exe" va "python3.exe" - Tat OFF ca hai
echo.
echo    Buoc 3: Dong cua so nay va mo lai start.bat
echo.
goto :done

:: ── Subroutine: try a specific python.exe path ─────────────────────────────
:try
if not exist %1 goto :eof
%1 --version >nul 2>&1
if not errorlevel 1 (
    %1 start.py
    goto :done
)
goto :eof

:done
pause
