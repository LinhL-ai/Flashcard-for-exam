@echo off
title Flashcard Server
cd /d "%~dp0"

echo Starting server...
start "" cmd /c "python -m http.server 8080"
ping 127.0.0.1 -n 3 >nul
start "" "http://localhost:8080/flashcard_app.html"

echo.
echo Server is running at http://localhost:8080/flashcard_app.html
echo Press any key to stop the server and exit.
pause >nul
taskkill /F /IM python.exe >nul 2>&1
