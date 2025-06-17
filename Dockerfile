# Use official slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . /app

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --upgrade pip \
 && pip install -r requirements.txt

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Run your bot
CMD ["python", "bot.py"]


# Command to run your bot (adjust if needed)
CMD ["python", "bot.py"]
