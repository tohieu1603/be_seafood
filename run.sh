#!/bin/bash

# Script to run Django Backend

echo "🦞 Starting Seafood Backend..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Start server with Daphne (for WebSocket support)
echo "Starting Django server with Daphne (WebSocket support) at http://localhost:8000"
echo "API Docs: http://localhost:8000/api/docs"
echo "WebSocket: ws://localhost:8000/ws/orders/"
daphne -b 0.0.0.0 -p 8000 config.asgi:application
