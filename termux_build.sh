#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python clang libjpeg-turbo libffi openssl ffmpeg git
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
echo "Build complete. Configure .env, then run: bash termux_start.sh"
