#!/bin/bash

echo "clean up the build folder..."
rm -rf dist/* build/*

echo "packing..."
pyinstaller --onefile --windowed --name LogInsight --add-data "icons:icons" log_insight.py

echo "packing done, installer located in dist folder."