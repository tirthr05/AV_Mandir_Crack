#!/usr/bin/env bash
set -e

# Install Node.js deps for POT server
npm install -g @githubnext/github-actions-parser 2>/dev/null || true

# Clone bgutil POT server
rm -rf /opt/bgutil-server
git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil-server
cd /opt/bgutil-server/server
npm ci
npx tsc || node_modules/.bin/tsc

echo "BGUtil POT server built successfully"

# Install Python packages
pip install -r requirements.txt
