@echo off
REM build_v107 via raw PyInstaller (like original build_v106.bat, but with new venv)
setlocal
set LOG=%~dp0build_v107_raw.log
echo [%date% %time%] build v1.0.7 (raw PyInstaller) start > "%LOG%"
cd /d "%~dp0"
C:\Users\yason\.minimax\workspace\python-embed-311\tools\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name PalworldFriendModInstaller ^
    --icon "%~dp0installer.ico" ^
    --add-data "%~dp0installer.ico;." ^
    --add-data "%~dp0friend-catalog.json;." ^
    --distpath dist ^
    --workpath build_v107_raw ^
    --specpath build_v107_raw ^
    --noconfirm ^
    friend_flet.py >> "%LOG%" 2>&1
echo [%date% %time%] build rc=%errorlevel% >> "%LOG%"
if errorlevel 1 exit /b 1
echo [%date% %time%] done. output: dist\PalworldFriendModInstaller.exe >> "%LOG%"
dir dist\PalworldFriendModInstaller.exe >> "%LOG%"
endlocal
exit /b 0
