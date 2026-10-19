#!/bin/sh
set -e
uvicorn mock_odata.app:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
trap 'kill $SERVER_PID' EXIT
sleep 2
export ODATA_BASE_URL=http://127.0.0.1:8000 LAKEHOUSE_ROOT=./lakehouse FULL_REFRESH=true
python3 -m ingest.pipeline
ls -la lakehouse/silver
