@echo off
chcp 65001 >nul 2>&1
title VN Stock ML Lab
cd /d "%~dp0"

echo.
echo  +--------------------------------------------------+
echo  ^|         VN Stock ML Lab  --  Khoi dong           ^|
echo  +--------------------------------------------------+
echo.

:: ── 1. py.exe (Python Launcher for Windows) ────────────────────────────────
::    Duoc cai kem voi Python chinh thuc, la cach chac chan nhat.
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 start.py
    goto :done
)

:: ── 2. python / python3 trong PATH ─────────────────────────────────────────
::    Windows 10/11 co "python.exe" gia (Store alias) vuot qua lenh "where".
::    Kiem tra bang cach chay "--version" va loc output "Python 3.x.x".
::    Store stub khong in "Python 3..." -> findstr tra ve loi -> bo qua.
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

:: ── 3. Tim Python trong cac duong dan cai dat mac dinh ─────────────────────
call :try "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
call :try "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
call :try "%PROGRAMFILES%\Python313\python.exe"
call :try "%PROGRAMFILES%\Python312\python.exe"
call :try "%PROGRAMFILES%\Python311\python.exe"
call :try "%PROGRAMFILES%\Python310\python.exe"

:: ── Python khong tim thay ─────────────────────────────────────────────────
echo.
echo  [LOI] Khong tim thay Python 3.10 tro len tren may tinh nay.
echo.
echo  CACH CAI PYTHON (doc ky tung buoc):
echo.
echo  Buoc 1: Mo trinh duyet, vao dia chi:
echo          https://www.python.org/downloads/
echo.
echo  Buoc 2: Click nut "Download Python 3.12.x"
echo.
echo  Buoc 3: Chay file .exe vua tai xuong
echo          !!! QUAN TRONG !!! Truoc khi bam "Install Now":
echo          Hay TICK vao o "Add Python to PATH"
echo          (o nay nam o DUOI CUNG cua man hinh cai dat dau tien)
echo.
echo  Buoc 4: Bam "Install Now" va cho cai dat hoan tat
echo.
echo  Buoc 5: Dong cua so nay va mo lai start.bat
echo.
echo  ---- Neu da cai Python nhung van bi loi nay: ----
echo  Vao Settings ^> Apps ^> Advanced app settings ^> App execution aliases
echo  Tim "python.exe" va "python3.exe" -> Tat OFF ca hai -> Chay lai start.bat
echo.
goto :done

:: ── Subroutine: thu chay Python tai duong dan cu the ───────────────────────
:try
if not exist %1 goto :eof
%1 --version >nul 2>&1
if not errorlevel 1 (
    %1 start.py
    goto :done
)
goto :eof

:done
echo.
pause
