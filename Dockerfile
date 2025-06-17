FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy your app files
COPY . /app

# Install dependencies
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Set default command to run your bot
CMD ["python", "bot.py"]
