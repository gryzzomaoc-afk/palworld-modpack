@echo off
REM build_v108 via raw PyInstaller (v1.0.8 with repo-driven mod discovery)
REM v1.0.8 no longer bundles friend-catalog.json — installer uses
REM fetch_mods_from_github() to discover mods/ on GitHub at runtime.
setlocal
set LOG=%~dp0build_v108_raw.log
echo [%date% %time%] build v1.0.8 (raw PyInstaller) start > "%LOG%"
cd /d "%~dp0"
C:\Users\yason\.minimax\workspace\python-embed-311\tools\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name PalworldFriendModInstaller ^
    --icon "%~dp0installer.ico" ^
    --add-data "%~dp0installer.ico;." ^
    --distpath dist ^
    --workpath build_v108_raw ^
    --specpath build_v108_raw ^
    --noconfirm ^
    friend_flet.py >> "%LOG%" 2>&1
echo [%date% %time%] build rc=%errorlevel% >> "%LOG%"
if errorlevel 1 exit /b 1
echo [%date% %time%] done. output: dist\PalworldFriendModInstaller.exe >> "%LOG%"
dir dist\PalworldFriendModInstaller.exe >> "%LOG%"
endlocal
exit /b 0
