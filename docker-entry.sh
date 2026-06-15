#!/bin/bash
set -e

cd /app
if [ -f requirements.txt ]; then
    pip install --no-cache-dir -q -r requirements.txt
fi
python3 -u -m uc_intg_weather
