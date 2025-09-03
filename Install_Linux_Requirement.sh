#!/bin/bash

echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "Installing ExifTool..."
sudo apt update
sudo apt install -y exiftool

echo
echo "Done installation!"
echo "Use this to make Start.sh Exicutable: chmod +x Start.sh"
echo "Then use ./start.sh to Start the program"