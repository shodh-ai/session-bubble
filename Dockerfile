#-----------------------------------------------------------------------------
# Stage 1: Builder
# This stage installs dependencies and Python packages. It contains build tools.
#-----------------------------------------------------------------------------
FROM python:3.11-bookworm as builder

# Set environment variables for the build
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-cache

# 1. Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg wget unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python packages to a specific location
COPY requirements.txt .
RUN pip install --target=/opt/app/packages -r requirements.txt

# 3. Install Playwright browsers and dependencies as root
RUN playwright install-deps chromium && \
    playwright install chromium --with-deps

#-----------------------------------------------------------------------------
# Stage 2: Final Image
# This stage creates the lean, final image for production.
#-----------------------------------------------------------------------------
FROM python:3.11-bookworm

# Set environment variables that will be used by the non-root user
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright \
    # Add the installed packages to the Python path
    PYTHONPATH="/home/appuser/app:/opt/app/packages" \
    PATH="/home/appuser/.local/bin:${PATH}" \
    DATABASE_PATH="/home/appuser/data/aurora_agent.db" \
    DISPLAY=":99"

# 1. Install ONLY runtime system dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    xvfb dbus-x11 x11-utils x11vnc openbox \
    # Runtime dependencies for Chromium
    libgl1-mesa-glx libxtst6 libgtk-3-0 libasound2 libnss3 libxss1 libdrm2 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy the supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 3. Create the non-root user and necessary directories
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/data /home/appuser/app && \
    chown -R appuser:appuser /home/appuser

# 4. Copy pre-installed Python packages and Playwright browsers from the builder stage
COPY --from=builder /opt/app/packages /opt/app/packages
COPY --from=builder ${PLAYWRIGHT_BROWSERS_PATH} /home/appuser/.cache/ms-playwright
RUN chown -R appuser:appuser /home/appuser/.cache

WORKDIR /home/appuser/app
USER appuser

# 5. Copy the application source code
COPY --chown=appuser:appuser . .

# Expose the VNC port
EXPOSE 6901

# The main command to run the container.
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]