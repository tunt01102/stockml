@echo off
REM -- Trick: cmd /k dam bao cua so KHONG BAO GIO tu dong dong ----------------
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
:: BUOC 1: Tim Python 3.10+  (tu dong cai neu khong tim thay)
:: ============================================================
echo  [1/4] Tim Python 3.10+...

REM 1a: Cac lenh co san trong PATH
for %%P in (python3.13 python3.12 python3.11 python3.10 python3 python) do (
    if "!PYTHON!" == "" (
        where %%P >nul 2>&1
        if not errorlevel 1 (
            %%P -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
            if not errorlevel 1 set PYTHON=%%P
        )
    )
)

REM 1b: Duong dan cai dat mac dinh (chua them vao PATH sau khi cai moi)
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

REM 1c: py.exe launcher -- lay duong dan python.exe thuc su
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

REM -- Tu dong cai Python 3.12 neu van chua tim thay --------------------------
if "!PYTHON!" == "" (
    echo        Chua tim thay -- dang tu dong cai Python 3.12...

    REM Xac dinh kien truc CPU (amd64 hoac arm64)
    set PY_ARCH=amd64
    if "%PROCESSOR_ARCHITECTURE%"=="ARM64" set PY_ARCH=arm64

    REM Cach A: winget (co san tren Windows 10 1709+ va Windows 11)
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo        Dung winget de cai Python 3.12...
        winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        REM Quet lai cac duong dan biet (PATH chua cap nhat trong session nay)
        for %%D in (
            "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
            "%ProgramFiles%\Python312\python.exe"
            "C:\Python312\python.exe"
        ) do (
            if "!PYTHON!" == "" (
                if exist %%D (
                    %%D -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
                    if not errorlevel 1 set PYTHON=%%D
                )
            )
        )
        REM Thu py launcher sau khi winget cai xong
        if "!PYTHON!" == "" (
            where py >nul 2>&1
            if not errorlevel 1 (
                for /f "tokens=*" %%P in ('py -3.12 -c "import sys;print(sys.executable)" 2^>nul') do (
                    if "!PYTHON!" == "" set PYTHON=%%P
                )
                if "!PYTHON!" == "" (
                    for /f "tokens=*" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
                        if "!PYTHON!" == "" set PYTHON=%%P
                    )
                )
            )
        )
    ) else (
        REM Cach B: Tai file cai dat .exe qua PowerShell
        echo        winget khong co -- dang tai Python 3.12 tu python.org...
        set PY_VER_DL=3.12.9
        set PY_URL=https://www.python.org/ftp/python/!PY_VER_DL!/python-!PY_VER_DL!-!PY_ARCH!.exe
        echo        URL: !PY_URL!
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;try{Invoke-WebRequest '!PY_URL!' -OutFile '%TEMP%\python_setup.exe' -UseBasicParsing;exit 0}catch{exit 1}"
        REM Kiem tra file hop le: phai lon hon 5 MB (tranh luu trang loi HTML)
        set DL_OK=0
        if exist "%TEMP%\python_setup.exe" (
            for %%S in ("%TEMP%\python_setup.exe") do (
                if %%~zS GTR 5000000 set DL_OK=1
            )
        )
        if "!DL_OK!" == "1" (
            echo        Dang cai dat Python 3.12 ^(chi nguoi dung hien tai, khong can Admin^)...
            "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
            del /f "%TEMP%\python_setup.exe" >nul 2>&1
            for %%D in (
                "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
                "%ProgramFiles%\Python312\python.exe"
                "C:\Python312\python.exe"
            ) do (
                if "!PYTHON!" == "" (
                    if exist %%D (
                        %%D -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
                        if not errorlevel 1 set PYTHON=%%D
                    )
                )
            )
            if "!PYTHON!" == "" (
                where py >nul 2>&1
                if not errorlevel 1 (
                    for /f "tokens=*" %%P in ('py -3.12 -c "import sys;print(sys.executable)" 2^>nul') do (
                        if "!PYTHON!" == "" set PYTHON=%%P
                    )
                )
            )
        ) else (
            if exist "%TEMP%\python_setup.exe" del /f "%TEMP%\python_setup.exe" >nul 2>&1
            echo        Tai that bai hoac file khong hop le.
        )
    )
)

if "!PYTHON!" == "" (
    echo.
    echo  [LOI] Khong tim thay va khong the tu dong cai Python.
    echo.
    echo  CAI PYTHON THU CONG:
    echo    1. Vao: https://www.python.org/downloads/
    echo    2. Click "Download Python 3.12.x"
    echo    3. Mo file .exe vua tai
    echo    4. QUAN TRONG: Tick "Add Python to PATH" ^(o DUOI CUNG^)
    echo    5. Bam Install Now -- sau do mo lai start.bat
    echo.
    echo  Neu da cai ma van loi:
    echo    Settings ^> Apps ^> Advanced app settings ^> App execution aliases
    echo    Tim python.exe va python3.exe -^> Tat OFF -^> Chay lai
    echo.
    start "" "https://www.python.org/downloads/"
    goto :end
)

for /f "tokens=*" %%V in ('"!PYTHON!" --version 2>&1') do set PY_VER=%%V
echo        OK - !PY_VER!
echo.

REM -- Kiem tra pip co san (Python 3.10+ thuong co san, kiem tra cho chac) ----
"!PYTHON!" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo        Bootstrapping pip...
    "!PYTHON!" -m ensurepip --upgrade >nul 2>&1
    if errorlevel 1 (
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;try{Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py' -UseBasicParsing}catch{exit 1}"
        if exist "%TEMP%\get-pip.py" (
            "!PYTHON!" "%TEMP%\get-pip.py" --quiet
            del /f "%TEMP%\get-pip.py" >nul 2>&1
        )
    )
)

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
    echo        venv that bai, thu cai virtualenv...
    "!PYTHON!" -m pip install virtualenv --quiet
    "!PYTHON!" -m virtualenv "!VENV!"
)

if not exist "!VENV!\Scripts\python.exe" (
    echo.
    echo  [LOI] Khong the tao moi truong ao tai: !VENV!
    echo  - Kiem tra o dia con trong ^(can ^>= 500 MB^)
    echo  - Thu chay start.bat voi quyen Admin ^(chuot phai -^> Run as administrator^)
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

echo        Dang cai dat ^(lan dau mat 3-5 phut -- KHONG TAT cua so nay^)...
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
:: BUOC 4: Tim cong va khoi dong server
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
    echo  [LOI] Khong tim duoc cong trong ^(8000-8009 deu ban^).
    goto :end
)

if not "!PORT!" == "8000" (
    echo        Cong 8000 dang ban -- dung cong !PORT!
)

echo        Khoi dong tren cong !PORT!...

REM Khoi dong uvicorn trong background, /D dat working dir la backend/
start "" /B /D "%~dp0backend" "!PYTHON!" -m uvicorn main:app --host 127.0.0.1 --port !PORT! --log-level warning --no-access-log

REM Cho server san sang: kiem tra port, toi da 30 giay
set /a cnt=0
:wait_loop
    timeout /t 1 /nobreak >nul
    netstat -ano | findstr ":!PORT! " | findstr "LISTENING" >nul 2>&1
    if not errorlevel 1 goto :server_ready
    set /a cnt+=1
    if !cnt! geq 30 (
        echo.
        echo  [LOI] Server khong khoi dong duoc sau 30 giay.
        echo  Xem loi uvicorn phia tren ^(neu co^).
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
