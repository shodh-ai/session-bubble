#!/bin/bash
set -e

# --- Configuration ---
XVFB_DISPLAY=":99"
# This resolution is better for modern web pages
XVFB_WHD="1920x1080x24"
VNC_CLIP_GEOMETRY="1920x1080"
VNC_PORT="6901"

# --- Start Virtual Framebuffer (Xvfb) ---
# The logic you had to wait for the socket was excellent. Let's keep it.
echo "Starting Xvfb on display ${XVFB_DISPLAY}..."
Xvfb ${XVFB_DISPLAY} -screen 0 ${XVFB_WHD} -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Use 'xdpyinfo' for a more robust check that the X server is truly ready
echo "Waiting for X server to be ready..."
timeout 15s bash -c "
  until xdpyinfo -display ${XVFB_DISPLAY} >/dev/null 2>&1; do
    sleep 0.5;
  done"
if [ $? -ne 0 ]; then
    echo "ERROR: Xvfb failed to start within 15 seconds."
    exit 1
fi
echo "X server is ready."
export DISPLAY=${XVFB_DISPLAY}

# --- Start Services ---
echo "Starting x11vnc server on port ${VNC_PORT}..."
# Key flags:
# -clip 1920x1080+0+0: Ensures the VNC viewport matches the virtual screen size.
# -ncache 10: A performance optimization for repeated screen areas.
# -shared: Allows multiple clients to connect and view the same session.
x11vnc -display ${XVFB_DISPLAY} -forever -nopw -listen 0.0.0.0 -rfbport ${VNC_PORT} -clip ${VNC_CLIP_GEOMETRY}+0+0 -ncache 10 -shared &

echo "Starting FastAPI application as user 'appuser'..."
# The 'exec' command is important: it replaces the shell process with uvicorn.
# This ensures that signals (like Ctrl+C) are passed correctly to the Python app.
exec gosu appuser uvicorn aurora_agent.app:app --host 0.0.0.0 --port 8000