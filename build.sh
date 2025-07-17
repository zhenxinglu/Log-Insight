#!/bin/bash

echo "clean up the build folder..."
rm -rf dist/* build/*

echo "reading version..."
version=$(cat version.txt)
echo "version: $version"

echo "packing..."
pyinstaller --onefile --windowed --name "LogInsight-$version" --icon="icons/logo.ico" --add-data "icons:icons" log_insight.py

echo "packing done, installer located in dist folder."