@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo   OpenTruck - Installer Builder v1.1
echo ============================================================
echo.

echo [1/5] Preparing build environment...

if exist "dist" rmdir /S /Q "dist" 2>nul

if not exist "raw captures" mkdir "raw captures" 2>nul
if not exist "vehicle logs" mkdir "vehicle logs" 2>nul
if not exist "build" mkdir "build" 2>nul

echo.
echo [2/5] Checking dependencies...

set "PY=python"
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Python not found
    goto :fail
)
echo   [PASS] Python interpreter

"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    set "FAILMSG=PyInstaller not installed"
    goto :fail
)
echo   [PASS] PyInstaller

"%PY%" -c "import PySide6; import reportlab" >nul 2>&1
if errorlevel 1 (
    set "FAILMSG=Missing packages (PySide6/reportlab)"
    goto :fail
)
echo   [PASS] Required packages installed

rem Locate the Inno Setup compiler (user-local install via winget, or machine-wide).
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo FAIL: Inno Setup 6 not found ^(install with: winget install JRSoftware.InnoSetup^)
    goto :fail
)
echo   [PASS] Inno Setup 6: !ISCC!

rem Ensure the Microsoft VC++ redistributable is present (bundled offline).
if not exist "%~dp0redist" mkdir "%~dp0redist" 2>nul
if exist "%~dp0redist\vc_redist.x64.exe" (
    echo   [PASS] VC++ redistributable present
) else (
    echo   [INFO] Downloading Microsoft VC++ 2015-2022 Redistributable ^(x64^)...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%~dp0redist\vc_redist.x64.exe' -UseBasicParsing"
    if not exist "%~dp0redist\vc_redist.x64.exe" (
        echo FAIL: Could not download VC++ redistributable
        goto :fail
    )
    echo   [PASS] VC++ redistributable downloaded
)

echo.
echo ============================================================
echo   All dependencies verified
echo ============================================================
echo.

echo [2b/5] Bumping build number...
"%PY%" "%~dp0bump_version.py" > "%~dp0.buildver.tmp"
set /p APPVER=<"%~dp0.buildver.tmp"
del "%~dp0.buildver.tmp" 2>nul
if not defined APPVER (
    echo FAIL: Could not bump build number
    goto :fail
)
echo   [PASS] Version now !APPVER!

rem Ship this build's changelog section inside the app: the once-per-update
rem popup shows it at startup (generated, git-ignored).
"%PY%" "%~dp0make_release_notes.py"

echo [3/5] Building OpenTruck application bundle ^(onedir^)...
"%PY%" -m PyInstaller --noconfirm --clean --specpath specfiles --name OpenTruck --onedir --windowed --icon "%~dp0icon.ico" --add-data "%~dp0MainWindow.ui;." --add-data "%~dp0icon.ico;." --collect-all reportlab app.py 2>&1 >>nul
if errorlevel 1 (
    echo FAIL: App build failed
    goto :fail
)
echo   [PASS] Application bundle built at dist\OpenTruck\

echo [4/5] Building 32-bit bridge...
set "PY32="
for %%P in (
    "C:\Program Files (x86)\Python313-32\python.exe"
    "C:\Program Files (x86)\Python312-32\python.exe"
    "C:\Program Files (x86)\Python311-32\python.exe"
    "C:\Python313-32\python.exe"
    "C:\Python312-32\python.exe"
    "C:\Python311-32\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311-32\python.exe"
) do if not defined PY32 if exist %%P set "PY32=%%~P"

if not defined PY32 (
    echo   [SKIP] No 32-bit Python found - 32-bit-only adapter drivers will be unsupported
) else (
    echo   [INFO] 32-bit Python: !PY32!
    "!PY32!" -m PyInstaller --noconfirm --clean --name OpenTruckBridge32 --onefile --console --specpath "%~dp0specfiles" --distpath "%~dp0dist\bridge32" --workpath "%~dp0build\bridge32" "%~dp0rp1210_bridge.py" >>nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Bridge build failed - 32-bit-only adapters will be unsupported
    ) else (
        copy /Y "%~dp0dist\bridge32\OpenTruckBridge32.exe" "%~dp0dist\OpenTruck\OpenTruckBridge32.exe" >nul
        echo   [PASS] 32-bit bridge OpenTruckBridge32.exe bundled next to OpenTruck.exe
    )
)

rem --- Optional code signing ---------------------------------------------
rem A SELF-SIGNED certificate does NOT clear SmartScreen (it only removes the
rem UAC "Unknown publisher" line, and only where the root is imported). This
rem hook is for a real OV/EV certificate or Azure Trusted Signing - the only
rem things that build publisher reputation. App binaries are signed BEFORE Inno
rem packages them, so what lands in Program Files is signed too.
rem   set SIGN_CERT=C:\certs\opentruck.pfx     (pfx path, or a cert thumbprint)
rem   set SIGN_PASS=<pfx password>              (omit for a token/HSM cert)
rem   set SIGN_TOOL=C:\path	o\signtool.exe    (optional; otherwise found on PATH)
if defined SIGN_CERT (
    call :sign "%~dp0dist\OpenTruck\OpenTruck.exe"
    if exist "%~dp0dist\OpenTruck\OpenTruckBridge32.exe" call :sign "%~dp0dist\OpenTruck\OpenTruckBridge32.exe"
) else (
    echo   [SKIP] No signing certificate configured ^(SIGN_CERT not set^)
)

echo [5/5] Compiling installer with Inno Setup...
"!ISCC!" "%~dp0OpenTruckInstaller.iss"
if errorlevel 1 (
    echo FAIL: Inno Setup compile failed
    goto :fail
)

set "SETUP_OUT="
for %%F in ("%~dp0dist\OpenTruckSetup-*.exe") do set "SETUP_OUT=%%F"
if defined SETUP_OUT (
    if defined SIGN_CERT call :sign "!SETUP_OUT!"
    echo   [PASS] Installer created at !SETUP_OUT!
    rem SHA-256 sidecar: <hash>  <installer name>, the format sha256sum -c
    rem expects, so a downloader can verify they got the real file.
    for %%N in ("!SETUP_OUT!") do set "SETUP_NAME=%%~nxN"
    for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '!SETUP_OUT!').Hash.ToLower()" 2^>nul') do set "SETUP_SHA=%%H"
    if defined SETUP_SHA (
        echo   [PASS] SHA-256: !SETUP_SHA!
        >"!SETUP_OUT!.sha256" echo !SETUP_SHA!  !SETUP_NAME!
    )
) else (
    echo FAIL: Installer output missing
    goto :fail
)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo Installer: !SETUP_OUT!
echo.
echo Features:
echo   - Fully offline (no internet needed on the target PC)
echo   - Bundles Python, Qt/PySide6, reportlab and the VC++ runtime
echo   - Installs the Microsoft VC++ 2015-2022 Redistributable silently
echo   - Creates Desktop and Start Menu shortcuts
echo   - Writable log folders (raw captures\, vehicle logs\)
echo   - Requires admin/UAC ^(to install the VC++ runtime^)
echo ============================================================

goto :end

:fail
echo.
echo BUILD FAILED
if defined FAILMSG echo   Reason: !FAILMSG!
echo Fix the issue and re-run build.bat

:end
if defined NOPAUSE exit /b 0
pause
goto :eof

rem --- helpers --------------------------------------------------------------
:sign
rem Sign one file. A missing signtool or a failed signature must never fail the
rem build, but it must be loud: a silently unsigned installer is how you end up
rem shipping something SmartScreen blocks while believing it was signed.
set "TARGET=%~1"
set "STOOL=%SIGN_TOOL%"
if not defined STOOL for /f "delims=" %%S in ('where signtool 2^>nul') do if not defined STOOL set "STOOL=%%S"
if not defined STOOL (
    echo   [WARN] signtool not found - %~nx1 left unsigned ^(install the Windows SDK^)
    exit /b 0
)
set "SARGS=/fd sha256 /tr http://timestamp.digicert.com /td sha256"
if defined SIGN_PASS (
    "!STOOL!" sign /f "!SIGN_CERT!" /p "!SIGN_PASS!" !SARGS! "!TARGET!"
) else (
    "!STOOL!" sign /sha1 "!SIGN_CERT!" !SARGS! "!TARGET!"
)
if errorlevel 1 (
    echo   [WARN] Signing failed for %~nx1 ^(continuing^)
) else (
    echo   [PASS] Signed %~nx1
)
exit /b 0
