# Stage 1: Base image with Python
FROM python:3.11-bookworm

# Set environment variables that will be used by the non-root user later
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright \
    PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH="/home/appuser/app" \
    DATABASE_PATH="/home/appuser/data/aurora_agent.db" \
    DISPLAY=":99"

# --- ROOT-LEVEL SETUP ---
# 1. Install all system dependencies, INCLUDING supervisor.
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl gnupg wget gosu unzip \
    xvfb dbus-x11 x11-utils x11vnc openbox \
    libgl1-mesa-glx libxtst6 libgtk-3-0 libasound2 libnss3 libxss1 libdrm2 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy requirements file and install Python packages GLOBALLY.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 3. Install Playwright browsers and their OS dependencies as root.
RUN playwright install-deps chromium && \
    playwright install chromium

# 4. Copy the supervisor configuration file into the container.
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# --- NON-ROOT USER SETUP ---
# 5. Create the non-root user.
RUN useradd --create-home --shell /bin/bash appuser

# 6. Explicitly set ownership of the entire home directory to the new user.
RUN chown -R appuser:appuser /home/appuser

# 7. Create database directory with proper permissions.
RUN mkdir -p /home/appuser/data && chown -R appuser:appuser /home/appuser/data

WORKDIR /home/appuser/app

# 8. Copy the entire application source code and set its ownership to the new user.
COPY --chown=appuser:appuser . .

# --- FINAL CONFIGURATION ---
# Expose the VNC port (the python scripts bind to localhost, not exposed)
EXPOSE 6901

USER appuser

# The main command to run the container. This starts supervisor,
# which in turn starts all of your services as the 'appuser'.
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
