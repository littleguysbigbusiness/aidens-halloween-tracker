@echo off
echo === Aiden's Halloween Tracker - Installer ===
echo.

where python >nul 2>nul
if errorlevel 1 goto :nopython

echo Installing dependencies (this can take a minute, especially the first time)...
python -m pip install -r requirements.txt
if errorlevel 1 goto :pipfail

if exist local_settings.py goto :skipcopy
copy local_settings.py.example local_settings.py >nul
echo Created local_settings.py from the template.
:skipcopy

echo.
echo Dependencies installed. Now let's configure your camera and (optionally) candy math.
echo.
python setup.py

echo.
echo === Setup complete! ===
echo Next: run pick_zone.py to draw your detection zone, then main.py to start tracking.
echo   python pick_zone.py
echo   python main.py
echo.
pause
goto :eof

:nopython
echo Python was not found on this machine.
echo Install Python 3.10+ from https://python.org (check "Add to PATH" during install), then run this again.
pause
exit /b 1

:pipfail
echo.
echo Dependency install failed - check the error above.
pause
exit /b 1
