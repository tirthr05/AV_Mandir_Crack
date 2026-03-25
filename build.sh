#!/usr/bin/env bash
# Install system deps
apt-get update && apt-get install -y ffmpeg nodejs npm

# Install Python deps
pip install -r requirements.txt

# Install the bgutil POT server (auto token generator)
npm install -g npm@latest
pip install -U bgutil-ytdlp-pot-provider
