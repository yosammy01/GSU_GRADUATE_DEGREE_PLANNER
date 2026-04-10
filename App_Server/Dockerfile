# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching
# This ensures that packages are only re-installed if requirements.txt changes
COPY requirements.txt .

# Install the necessary Python packages (Flask, Gunicorn, and MySQL connector)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of Flask application code (app.py, templates, etc.) 
# from local App_Server folder into the container's /app folder
COPY . .

# Expose port 5000 for the web application
EXPOSE 5000

# Start the application using Gunicorn for production-ready parallel processing
# -w 4: Spawns 4 parallel worker processes to handle multiple student requests
# -b 0.0.0.0:5000: Binds the server to all network interfaces on port 5000
# app:app: Points to the "app" instance variable inside your app.py file
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]