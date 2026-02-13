# Use a lightweight Python version
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file first
COPY requirements.txt .

# Install the tools (and upgrade pip just in case)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

# Tell the server how to run the bot
CMD ["python", "main.py"]
