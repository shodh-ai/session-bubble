# Stage 1: Base image with Python and essential build tools
FROM python:3.11-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# Install system dependencies required for Playwright, Chrome, and KasmVNC
# Using 'apt-get -y --no-install-recommends' for a smaller image
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    wget \
    xvfb \
    tini \
    gosu \
    dbus-x11 \
    x11-utils \
    libgl1-mesa-glx \
    libxtst6 \
    libxt6 \
    libx11-6 \
    libxext6 \
    libxfixes3 \
    libxdmcp6 \
    libxau6 \
    libdbus-1-3 \
    libglib2.0-0 \
    libgtk-3-0 \
    libasound2 \
    libnss3 \
    libxss1 \
    libdrm2 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    x11vnc \
    # Clean up apt-get cache
    && rm -rf /var/lib/apt/lists/*

# Install system dependencies for Playwright Chromium as root
RUN pip install playwright==1.44.0 && \
    playwright install-deps chromium && \
    pip uninstall -y playwright

# Create a non-root user and switch to it
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /home/appuser

WORKDIR /home/appuser/app

USER appuser

# Add the user's local bin to the PATH and set the PYTHONPATH
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH="/home/appuser/app:/home/appuser/app/aurora_agent"

# Copy and install dependencies as the non-root user
COPY --chown=appuser:appuser requirements.txt .
RUN pip install -r requirements.txt

# Now that Playwright is installed, install the browser binaries
RUN playwright install chromium

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Expose the ports for the FastAPI app and KasmVNC
EXPOSE 8000
EXPOSE 6901

# Switch back to root to allow the entrypoint script to run with sudo-like privileges
USER root

# Use tini as the main entrypoint to manage processes correctly
ENTRYPOINT ["/usr/bin/tini", "--", "./entrypoint.sh"]