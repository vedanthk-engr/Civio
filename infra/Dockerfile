# Use official light Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

# Set work directory
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY backend/ /app/

# Expose port and launch
EXPOSE 8000
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
