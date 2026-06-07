@echo off
REM -- Trick tu run_all.bat: cmd /k dam bao cua so KHONG BAO GIO tu dong dong -----------
REM    Lan dau (tu Explorer): _RELAUNCHED chua co -> relaunch trong cmd /k session
REM    Lan hai (ben trong cmd /k): _RELAUNCHED=1 -> chay thang vao logic chinh
if not defined _RELAUNCHED (
    set _RELAUNCHED=1
    cmd /k "%~f0" %*
    exit /b
)

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  +--------------------------------------------------+
echo  ^|         VN Stock ML Lab  --  Khoi dong           ^|
echo  +--------------------------------------------------+
echo.

set PYTHON=
set VENV=%~dp0venv

:: ============================================================
:: BUOC 1: Tim Python 3.10+
:: ============================================================
echo  [1/4] Tim Python 3.10+...

REM 1a: Cac lenh co san trong PATH, uu tien ban moi nhat
REM     Dung -c "exit()" de loc alias Microsoft Store (khong chay duoc)
for %%P in (python3.13 python3.12 python3.11 python3.10 python3 python) do (
    if "!PYTHON!" == "" (
        where %%P >nul 2>&1
        if not errorlevel 1 (
            %%P -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
            if not errorlevel 1 set PYTHON=%%P
        )
    )
)

REM 1b: Duong dan cai dat mac dinh (AppData per-user va ProgramFiles system-wide)
if "!PYTHON!" == "" (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%ProgramFiles%\Python313\python.exe"
        "%ProgramFiles%\Python312\python.exe"
        "%ProgramFiles%\Python311\python.exe"
        "%ProgramFiles%\Python310\python.exe"
        "%ProgramFiles(x86)%\Python313\python.exe"
        "%ProgramFiles(x86)%\Python312\python.exe"
        "%ProgramFiles(x86)%\Python311\python.exe"
        "%ProgramFiles(x86)%\Python310\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
    ) do (
        if "!PYTHON!" == "" (
            if exist %%D (
                %%D -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
                if not errorlevel 1 set PYTHON=%%D
            )
        )
    )
)

REM 1c: py.exe launcher -- lay duong dan python.exe thuc su tu py launcher
if "!PYTHON!" == "" (
    where py >nul 2>&1
    if not errorlevel 1 (
        for %%V in (3.13 3.12 3.11 3.10) do (
            if "!PYTHON!" == "" (
                for /f "tokens=*" %%P in ('py -%%V -c "import sys;print(sys.executable)" 2^>nul') do (
                    if "!PYTHON!" == "" (
                        "%%P" -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
                        if not errorlevel 1 set PYTHON=%%P
                    )
                )
            )
        )
    )
)

if "!PYTHON!" == "" (
    echo.
    echo  [LOI] Khong tim thay Python 3.10 tro len.
    echo.
    echo  CACH CAI PYTHON:
    echo    1. Vao: https://www.python.org/downloads/
    echo    2. Click "Download Python 3.12.x"
    echo    3. Mo file .exe vua tai
    echo    4. QUAN TRONG: Tick "Add Python to PATH" (o DUOI CUNG)
    echo    5. Bam Install Now -- sau do mo lai start.bat
    echo.
    echo  Neu da cai ma van loi:
    echo    Settings ^> Apps ^> Advanced app settings ^> App execution aliases
    echo    Tim python.exe va python3.exe -^> Tat OFF -^> Chay lai
    echo.
    goto :end
)

for /f "tokens=*" %%V in ('"!PYTHON!" --version 2>&1') do set PY_VER=%%V
echo        OK - !PY_VER!
echo.

:: ============================================================
:: BUOC 2: Tao / kiem tra moi truong ao (venv)
:: ============================================================
echo  [2/4] Tao / kiem tra moi truong ao...

if exist "!VENV!\Scripts\python.exe" (
    echo        OK - da co san
    goto :venv_ok
)

REM Venv ton tai nhung thieu python.exe -> bi hong, xoa lai
if exist "!VENV!\" (
    echo        Phat hien venv bi hong -- dang xoa de tao lai...
    rmdir /s /q "!VENV!" 2>nul
)

echo        Dang tao ^(chi lam mot lan^)...
"!PYTHON!" -m venv "!VENV!" 2>nul
if errorlevel 1 (
    REM venv module co the chua co, thu cai virtualenv
    echo        venv that bai, thu cai virtualenv...
    "!PYTHON!" -m pip install virtualenv --quiet
    "!PYTHON!" -m virtualenv "!VENV!"
)

if not exist "!VENV!\Scripts\python.exe" (
    echo.
    echo  [LOI] Khong the tao moi truong ao tai: !VENV!
    echo  - Kiem tra o dia con trong (can ^>= 500 MB^)
    echo  - Thu chay start.bat voi quyen Admin (chuot phai -^> Run as administrator)
    echo.
    goto :end
)
echo        OK - da tao xong

:venv_ok
REM Tu day dung Python ben trong venv
set PYTHON=!VENV!\Scripts\python.exe
echo.

:: ============================================================
:: BUOC 3: Cai dat / kiem tra thu vien
:: ============================================================
echo  [3/4] Cai dat / kiem tra thu vien...

REM Kiem tra nhanh: neu cac thu vien chinh da co thi bo qua
"!PYTHON!" -c "import fastapi, uvicorn, sklearn, pandas, arch" >nul 2>&1
if not errorlevel 1 (
    echo        OK - da co san
    goto :packages_ok
)

echo        Dang cai dat (lan dau mat 3-5 phut -- KHONG TAT cua so nay^)...
"!PYTHON!" -m pip install --upgrade pip --quiet >nul 2>&1
"!PYTHON!" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [LOI] Cai dat thu vien that bai.
    echo  - Kiem tra ket noi internet
    echo  - Thu xoa thu muc venv\ roi chay lai
    echo.
    goto :end
)
echo        OK - cai dat xong

:packages_ok
echo.

:: ============================================================
:: BUOC 4: Khoi dong server
:: ============================================================
echo  [4/4] Tim cong va khoi dong server...

REM Tim cong trong (8000-8009)
set PORT=
for %%P in (8000 8001 8002 8003 8004 8005 8006 8007 8008 8009) do (
    if "!PORT!" == "" (
        netstat -ano | findstr ":%%P " | findstr "LISTENING" >nul 2>&1
        if errorlevel 1 set PORT=%%P
    )
)

if "!PORT!" == "" (
    echo  [LOI] Khong tim duoc cong trong (8000-8009 deu ban).
    goto :end
)

if not "!PORT!" == "8000" (
    echo        Cong 8000 dang ban -- dung cong !PORT!
)

echo        Khoi dong tren cong !PORT!...

REM Khoi dong uvicorn trong background (start /B)
REM /D dat working directory cho uvicorn (can thiet de import main:app)
start "" /B /D "%~dp0backend" "!PYTHON!" -m uvicorn main:app --host 127.0.0.1 --port !PORT! --log-level warning --no-access-log

REM Cho server san sang: kiem tra port mo, toi da 30 giay
set /a cnt=0
:wait_loop
    timeout /t 1 /nobreak >nul
    netstat -ano | findstr ":!PORT! " | findstr "LISTENING" >nul 2>&1
    if not errorlevel 1 goto :server_ready
    set /a cnt+=1
    if !cnt! geq 30 (
        echo.
        echo  [LOI] Server khong khoi dong duoc sau 30 giay.
        echo  Xem loi uvicorn phia tren (neu co).
        echo  Thu xoa thu muc venv\ roi chay lai.
        echo.
        goto :end
    )
goto :wait_loop

:server_ready
set URL=http://127.0.0.1:!PORT!
echo.
echo  +--------------------------------------------------+
echo  ^|  Dia chi  :  !URL!
echo  ^|  QUAN TRONG: GIU CUA SO NAY MO, KHONG DONG     ^|
echo  ^|  Nhan phim bat ky o day de dung server.        ^|
echo  +--------------------------------------------------+
echo.

REM Mo trinh duyet
start "" "!URL!"

REM Cho nguoi dung nhan phim de dung server
pause >nul

REM Tat uvicorn theo PID
echo  Dang dung server...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":!PORT! " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%P >nul 2>&1
)
echo  Server da dung. Co the dong cua so nay.

:end
echo.
endlocal
