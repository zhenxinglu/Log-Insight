@echo off
echo "clean up the build folder..."
del /Q dist\* 2>nul
del /Q build\* 2>nul

echo Reading version...
set /p VERSION=<version.txt
echo Version: %VERSION%

echo Packing...
pyinstaller --onefile --windowed --name "LogInsight-%VERSION%"  --add-data "icons;icons" log_insight.py

echo Packing done, installer located in dist folder.
pause