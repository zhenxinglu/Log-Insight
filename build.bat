@echo off
echo "clean up the build folder..."
del /Q dist\* 2>nul
del /Q build\* 2>nul

echo packing...
pyinstaller --onefile --windowed --name LogInsight log_insight.py

echo packing done, installer located in dist folder.
pause