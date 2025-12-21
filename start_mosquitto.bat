@echo off
echo Starting Mosquitto MQTT Broker...

REM Check if Mosquitto is installed
where mosquitto >nul 2>nul
if %errorlevel% neq 0 (
    echo Mosquitto is not found in PATH. Using default installation path...
    "C:\Program Files\mosquitto\mosquitto.exe" -v
) else (
    mosquitto -v
)
pause