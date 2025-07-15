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

# Install Playwright browsers and their dependencies as root
# This ensures system-level dependencies are in place before switching to a non-root user.
RUN pip install playwright==1.44.0 && \
    playwright install --with-deps webkit && \
    pip uninstall -y playwright

# Create a non-root user for better security
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /home/appuser
WORKDIR /home/appuser/app

# Add the user's local bin to the PATH and set the PYTHONPATH
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH="/home/appuser/app:/home/appuser/app/aurora_agent"

# Copy only the requirements file first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies for the appuser
# Playwright was already installed as part of requirements.txt, 
# and the browser binaries are already in the system cache.
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Expose the ports for the FastAPI app and KasmVNC
EXPOSE 8000
EXPOSE 6901

# Use tini as the main entrypoint to manage processes correctly
ENTRYPOINT ["/usr/bin/tini", "--", "./entrypoint.sh"]
