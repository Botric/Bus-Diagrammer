FROM python:3.11-slim AS base

# Create a user so the container does not run as root
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Use the non-root user
USER appuser

# Expose port 5000 for the Flask development server
EXPOSE 5620

# Run the application
CMD ["python", "app.py"]