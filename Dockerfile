# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements first to install dependencies
COPY requirements.txt .

# Install Python dependencies globally
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app's code
COPY . .

# Expose port for health check web server
EXPOSE 8080

# Command to run the bot
CMD ["python", "bot.py"]
