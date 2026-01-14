@echo off
echo Building CableRouteCAD...
pushd ..
if exist "%~dp0CableRouteCAD.spec" del "%~dp0CableRouteCAD.spec"
python -m PyInstaller --noconfirm --workpath "%~dp0build" --distpath "%~dp0dist" --specpath "%~dp0." --onefile --windowed --name "CableRouteCAD" --add-data "%CD%\assets;assets" --exclude-module PyQt5 --exclude-module PySide2 --exclude-module PySide6 main.py
popd
echo Build complete. Check the 'dist' folder.
pause
