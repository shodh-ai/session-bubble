# Stage 1: Base image with Python
FROM python:3.11-bookworm

# Set environment variables that will be used by the non-root user later
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright \
    PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH="/home/appuser/app"

# --- ROOT-LEVEL SETUP ---
# All commands in this section run as root, giving them full system access.

# 1. Install all system dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg wget tini gosu unzip \
    xvfb dbus-x11 x11-utils x11vnc \
    libgl1-mesa-glx libxtst6 libgtk-3-0 libasound2 libnss3 libxss1 libdrm2 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy requirements file and install Python packages GLOBALLY.
#    This is the key fix. We do this as root so packages are available to all users.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright browsers and their OS dependencies as root.
RUN playwright install-deps chromium && \
    playwright install chromium

# --- NON-ROOT USER SETUP ---
# Now that the system is fully prepared, we create and switch to our standard user.

# 4. Create the non-root user and the application directory.
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# 5. Copy the entire application source code and set its ownership to the new user.
#    This is the final step where we add our own code.
COPY --chown=appuser:appuser . .

# 6. Switch to the non-root user. This is a security best practice.
#    The entrypoint script will now start as this user by default (though gosu will handle it).
USER appuser

# --- FINAL CONFIGURATION ---
# Expose ports
EXPOSE 8000
EXPOSE 6901

# Switch back to root ONLY to allow the entrypoint script to use 'gosu'.
USER root

# Use tini to manage processes and execute the entrypoint script.
ENTRYPOINT ["/usr/bin/tini", "--", "./entrypoint.sh"]