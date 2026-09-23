#!/bin/bash

# Activate virtual environment if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Allow specifying port as the first argument (defaults to 8082)
PORT="${1:-8082}"

echo "Starting Django development server on port ${PORT}..."
python manage.py runserver "${PORT}"
