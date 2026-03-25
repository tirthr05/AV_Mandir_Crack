#!/usr/bin/env bash
set -e

echo "Starting BGUtil POT token server..."
cd /opt/bgutil-server/server
node build/main.js &

# Wait for POT server to be ready
for i in $(seq 1 15); do
    if curl -sf http://127.0.0.1:4416 > /dev/null 2>&1; then
        echo "POT server ready on port 4416"
        break
    fi
    echo "Waiting for POT server ($i/15)..."
    sleep 2
done

echo "Starting Flask with Gunicorn..."
exec gunicorn app:app \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 2 \
    --threads 4 \
    --timeout 300 \
    --keep-alive 5
