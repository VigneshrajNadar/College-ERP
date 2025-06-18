#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Set Python path
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate 