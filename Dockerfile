# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# System deps (if you need more, add here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
# (we install the ones referenced in the file header; if you later add a
# requirements.txt, you can switch to `COPY requirements.txt` + `pip install -r`)
RUN pip install --no-cache-dir \
    basyx-python-sdk \
    openai \
    python-telegram-bot

# Copy application code
COPY agent.py ./

# The app uses environment variables:
#   OPENAI_API_KEY
#   TELEGRAM_BOT_TOKEN
# You can pass them at runtime via -e / --env-file.

# Run the Telegram bot
CMD ["python", "agent.py"]

