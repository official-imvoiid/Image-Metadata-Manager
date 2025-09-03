@echo off
echo Installing Python packages...
pip install -r requirements.txt

echo Installing ExifTool...
winget install -e --id OliverBetz.ExifTool --silent

echo Done installation!
echo Now you can use Start.bat
echo
pause