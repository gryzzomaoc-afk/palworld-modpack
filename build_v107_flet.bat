@echo off
setlocal
set LOG=%~dp0build_v107_flet.log
echo [%date% %time%] build v1.0.7 (flet pack) start > "%LOG%"
cd /d "%~dp0"
C:\Users\yason\.minimax\workspace\python-embed-311\tools\Scripts\flet.exe pack friend_flet.py -n PalworldFriendModInstaller -i "E:\TOOL\installer.ico" --add-data "E:\TOOL\installer.ico;." --add-data "E:\TOOL\friend-catalog.json;." --product-name "PalworldFriendModInstaller" --product-version "1.0.7" --file-version "1.0.7.0" --company-name "CrazyChips" --file-description "Palworld 1-click mod installer" -y >> "%LOG%" 2>&1
echo [%date% %time%] build rc=%errorlevel% >> "%LOG%"
if errorlevel 1 exit /b 1
echo [%date% %time%] done. output: dist\PalworldFriendModInstaller.exe >> "%LOG%"
dir dist\PalworldFriendModInstaller.exe >> "%LOG%"
endlocal
exit /b 0
