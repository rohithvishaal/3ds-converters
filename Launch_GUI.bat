@echo off
REM 3DS Converter GUI Launcher
REM This batch file launches the modern GUI version of the 3DS converter

echo.
echo ╔════════════════════════════════════════════════╗
echo ║  3DS ROM Converter Pro - GUI Launcher         ║
echo ╚════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.9+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Launching 3DS ROM Converter Pro GUI...
echo.

REM Run the GUI
python 3ds_converter_gui.py

REM If the script exits with an error
if errorlevel 1 (
    echo.
    echo An error occurred. Please check the setup guide for troubleshooting.
    pause
)
