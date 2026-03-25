#!/usr/bin/env bash
# Start the POT token server in background on port 4416
npx --yes bgutil-ytdlp-pot-provider &

# Wait for it to be ready
sleep 3

# Start Flask
python app.py
