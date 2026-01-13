@echo off
echo Starting Vehicle Diagnostics System...

:: Start the Backend Server in a new window
echo Starting Backend Server (main.py)...
start "Vehicle Diagnostics Server" cmd /k "python main.py"

:: Wait for server to initialize
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

:: Start the Frontend UI
echo Starting Frontend UI (UI.py)...
start "Vehicle Diagnostics UI" cmd /k "python UI.py"

echo.
echo App launched!
echo If you close the server window, the app will lose connection capability.
