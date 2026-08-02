@echo off
REM build_v109: build .exe + wrap into friend-distribution .zip
REM v1.0.9: drops raw .exe in favor of .zip (avoids Windows Defender /
REM SmartScreen false positive that PyInstaller onefile triggers when
REM distributed as a bare .exe on GitHub Releases).
setlocal enabledelayedexpansion

set ROOT=%~dp0
set LOG=%ROOT%build_v109.log
echo [%date% %time%] build v1.0.9 start > "%LOG%"

REM --- Step 1: build the .exe via raw PyInstaller ---
cd /d "%ROOT%"
C:\Users\yason\.minimax\workspace\python-embed-311\tools\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name PalworldFriendModInstaller ^
    --icon "%ROOT%installer.ico" ^
    --add-data "%ROOT%installer.ico;." ^
    --distpath dist ^
    --workpath build_v109_raw ^
    --specpath build_v109_raw ^
    --noconfirm ^
    friend_flet.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] PyInstaller FAILED rc=%errorlevel% >> "%LOG%"
    exit /b 1
)

REM --- Step 2: compute SHA256 of the .exe ---
for /f "tokens=*" %%H in ('certutil -hashfile "dist\PalworldFriendModInstaller.exe" SHA256 ^| findstr /v "hash certutil"') do set "EXE_HASH=%%H"
set "EXE_HASH=%EXE_HASH: =%"
echo [%date% %time%] exe sha256=%EXE_HASH% >> "%LOG%"

REM --- Step 3: write SHA256.txt into the friend pack dir ---
> "%ROOT%friend_pack\SHA256.txt" echo PalworldFriendModInstaller.exe  %EXE_HASH%
echo [%date% %time%] wrote SHA256.txt >> "%LOG%"

REM --- Step 4: copy .exe into friend_pack\ ---
copy /Y "dist\PalworldFriendModInstaller.exe" "%ROOT%friend_pack\PalworldFriendModInstaller-v1.0.9.exe" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] copy .exe FAILED >> "%LOG%"
    exit /b 1
)
echo [%date% %time%] copied .exe into friend_pack\ >> "%LOG%"

REM --- Step 5: build the .zip via PowerShell Compress-Archive ---
powershell -NoProfile -NonInteractive -Command ^
    "Compress-Archive -Path '%ROOT%friend_pack\*' -DestinationPath '%ROOT%dist\PalworldFriendModInstaller-v1.0.9.zip' -Force" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] Compress-Archive FAILED >> "%LOG%"
    exit /b 1
)
echo [%date% %time%] wrote dist\PalworldFriendModInstaller-v1.0.9.zip >> "%LOG%"

REM --- Step 6: also drop a copy on the desktop for convenience ---
copy /Y "%ROOT%dist\PalworldFriendModInstaller-v1.0.9.zip" "%USERPROFILE%\OneDrive\桌面\PalworldFriendModInstaller-v1.0.9.zip" >> "%LOG%" 2>&1
echo [%date% %time%] copied zip to desktop rc=%errorlevel% >> "%LOG%"

REM --- Step 7: report ---
echo [%date% %time%] === final outputs === >> "%LOG%"
dir "%ROOT%dist\PalworldFriendModInstaller-v1.0.9.zip" >> "%LOG%"
dir "%ROOT%dist\PalworldFriendModInstaller.exe" >> "%LOG%"

echo [%date% %time%] done. >> "%LOG%"
endlocal
exit /b 0
