#!/bin/bash
set -e

# --- Configuration ---
XVFB_DISPLAY=":99"
XVFB_WHD="1280x960x24"
XVFB_SOCKET="/tmp/.X11-unix/X${XVFB_DISPLAY#:}"
XVFB_LOG_FILE="/tmp/xvfb.log"
START_TIMEOUT=15

# --- Start and Wait for Xvfb ---
echo "Starting Xvfb on display ${XVFB_DISPLAY}..."
Xvfb ${XVFB_DISPLAY} -screen 0 ${XVFB_WHD} -ac -fbdir /tmp -listen tcp >"${XVFB_LOG_FILE}" 2>&1 &
XVFB_PID=$!

echo "Waiting for Xvfb (PID: ${XVFB_PID}) to be ready..."
end_time=$((SECONDS + START_TIMEOUT))
while [ $SECONDS -lt $end_time ]; do
    # Check if the process is still running
    if ! kill -0 $XVFB_PID > /dev/null 2>&1; then
        echo "ERROR: Xvfb process died unexpectedly."
        echo "--- Xvfb Log ---"
        cat "${XVFB_LOG_FILE}"
        exit 1
    fi

    # Check for the socket file, which indicates the server is ready
    if [ -e "${XVFB_SOCKET}" ]; then
        echo "Xvfb socket found. Display is ready."
        export DISPLAY=${XVFB_DISPLAY}
        break
    fi
    sleep 0.5
done

if ! [ -e "${XVFB_SOCKET}" ]; then
    echo "ERROR: Xvfb failed to start within ${START_TIMEOUT} seconds."
    echo "--- Xvfb Log ---"
    cat "${XVFB_LOG_FILE}"
    exit 1
fi

# --- Start Services ---
echo "Starting x11vnc server..."
x11vnc -display ${XVFB_DISPLAY} -forever -nopw -listen 0.0.0.0 -rfbport 6901 &

echo "Starting FastAPI application..."
# Run the application as the non-root user (PYTHONPATH is now set in the Dockerfile).
exec gosu appuser bash -c 'uvicorn aurora_agent.app:app --host 0.0.0.0 --port 8000'

