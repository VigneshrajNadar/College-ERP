#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip
python3.13 -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PYTHONPATH=/opt/render/project/src
export DJANGO_SETTINGS_MODULE=college_management_system.settings

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate 