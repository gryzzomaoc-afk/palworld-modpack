@echo off
setlocal
set LOG=%~dp0build_v107.log
echo [%date% %time%] build v1.0.7 start > "%LOG%"
cd /d "%~dp0"
C:\Users\yason\.minimax\workspace\friend-tool-venv\Scripts\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name PalworldFriendModInstaller ^
    --icon "E:\TOOL\installer.ico" ^
    --add-data "E:\TOOL\installer.ico;." ^
    --add-data "E:\TOOL\friend-catalog.json;." ^
    --distpath "E:\TOOL\dist" ^
    --workpath "E:\TOOL\build_v107" ^
    --specpath "E:\TOOL\build_v107" ^
    --noconfirm ^
    "E:\TOOL\friend_flet.py" >> "%LOG%" 2>&1
echo [%date% %time%] build rc=%errorlevel% >> "%LOG%"
if errorlevel 1 exit /b 1
echo [%date% %time%] done. output: dist\PalworldFriendModInstaller.exe >> "%LOG%"
dir "E:\TOOL\dist\PalworldFriendModInstaller.exe" >> "%LOG%"
endlocal
exit /b 0
