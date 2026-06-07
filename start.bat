@echo off
chcp 65001 >nul 2>&1
title VN Stock ML Lab
cd /d "%~dp0"

echo.
echo  +--------------------------------------------------+
echo  ^|         VN Stock ML Lab  --  Khoi dong           ^|
echo  +--------------------------------------------------+
echo.

set "PYEXE="
set "PYARG="

:: ============================================================
:: BUOC 1: Tim Python 3.10+
:: ============================================================
echo  [1/3] Tim Python 3.10+...

:: 1a. py.exe (Python Launcher -- cai kem voi Python chinh thuc)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys;exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYEXE=py"
        set "PYARG=-3"
        goto :found_python
    )
)

:: 1b. python trong PATH (loai bo alias Microsoft Store)
python -c "import sys;exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    goto :found_python
)

:: 1c. python3 trong PATH
python3 -c "import sys;exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python3"
    goto :found_python
)

:: 1d. Duong dan cai dat mac dinh (AppData - per-user install)
call :try "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if defined PYEXE goto :found_python
call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PYEXE goto :found_python
call :try "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if defined PYEXE goto :found_python
call :try "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if defined PYEXE goto :found_python

:: 1e. Duong dan cai dat mac dinh (ProgramFiles - system-wide install)
call :try "%ProgramFiles%\Python313\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles%\Python312\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles%\Python311\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles%\Python310\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles(x86)%\Python313\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles(x86)%\Python312\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles(x86)%\Python311\python.exe"
if defined PYEXE goto :found_python
call :try "%ProgramFiles(x86)%\Python310\python.exe"
if defined PYEXE goto :found_python

:: Khong tim thay Python
echo.
echo  [LOI] Khong tim thay Python 3.10 tro len tren may nay.
echo.
echo  CACH CAI PYTHON (doc ky tung buoc):
echo.
echo    Buoc 1: Mo trinh duyet, vao:
echo            https://www.python.org/downloads/
echo.
echo    Buoc 2: Click "Download Python 3.12.x"
echo.
echo    Buoc 3: Mo file .exe vua tai xuong
echo            !!! QUAN TRONG !!! Truoc khi bam "Install Now":
echo            Hay TICK vao o "Add Python to PATH"
echo            (o nam o DUOI CUNG man hinh cai dat dau tien)
echo.
echo    Buoc 4: Bam "Install Now" va cho hoan tat
echo.
echo    Buoc 5: Dong cua so nay va mo lai start.bat
echo.
echo  Neu da cai Python nhung van bi loi nay:
echo    Vao Settings ^> Apps ^> Advanced app settings ^> App execution aliases
echo    Tim "python.exe" va "python3.exe" -^> Tat OFF ca hai -^> Chay lai
echo.
goto :end

:: ============================================================
:found_python
:: ============================================================
"%PYEXE%" %PYARG% -c "import sys;v=sys.version_info;print(f'       OK - Python {v.major}.{v.minor}.{v.micro}')"
echo.

:: ============================================================
:: BUOC 2: Tao moi truong ao (venv)
:: ============================================================
echo  [2/3] Tao / kiem tra moi truong ao...

if exist "venv\Scripts\python.exe" (
    echo        OK - da co san
    goto :venv_ready
)

:: Thu muc venv ton tai nhung thieu python.exe -> bi hong, xoa lai
if exist "venv\" (
    echo        Phat hien venv bi hong, dang xoa de tao lai...
    rmdir /s /q venv 2>nul
)

echo        Dang tao moi truong ao (chi lam mot lan, mat ~30 giay)...
"%PYEXE%" %PYARG% -m venv venv
if errorlevel 1 (
    echo.
    echo  [LOI] Khong the tao moi truong ao.
    echo  Thu cach khac:
    echo    - Kiem tra o dia con trong (can it nhat 500 MB)
    echo    - Chay start.bat voi quyen Admin (chuot phai -^> Run as administrator)
    goto :end
)

if not exist "venv\Scripts\python.exe" (
    echo.
    echo  [LOI] Tao venv xong nhung khong tim thay venv\Scripts\python.exe
    echo  Python co the bi cai thieu hoac quyen ghi bi han che.
    goto :end
)
echo        OK - da tao xong

:venv_ready
echo.

:: ============================================================
:: BUOC 3: Cai thu vien + Khoi dong server
:: ============================================================
echo  [3/3] Cai dat thu vien va khoi dong server...
echo.
echo  !! GIU CUA SO NAY MO de server tiep tuc chay
echo     Nhan Ctrl+C de dung server
echo.

:: Dat bien moi truong de start.py biet da co venv, bo qua buoc tao lai venv
set "_STOCKML_VENV=1"
venv\Scripts\python.exe start.py
set "START_EXIT=%ERRORLEVEL%"

if not %START_EXIT%==0 (
    echo.
    echo  [LOI] start.py thoat voi ma loi: %START_EXIT%
    echo  Xem thong bao phia tren de biet nguyen nhan.
    echo.
)
goto :end

:: ============================================================
:: Subroutine: thu 1 duong dan python cu the
:: Dung lai ngay khi tim thay (PYEXE da duoc dat)
:: ============================================================
:try
if defined PYEXE goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys;exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=%~1"
goto :eof

:: ============================================================
:end
:: ============================================================
echo.
pause
