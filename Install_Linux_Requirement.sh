#!/bin/bash

echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "Installing ExifTool..."
sudo apt update
sudo apt install -y exiftool

echo
echo "Done installation!"
echo "Now you can use start.sh"