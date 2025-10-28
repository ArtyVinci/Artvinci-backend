#!/usr/bin/env bash
# Build script for Render deployment

set -e

echo "🚀 Starting Artvinci Backend Build for Render..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run Django migrations (though we use MongoDB, some apps might need it)
echo "🗄️ Running Django checks..."
python manage.py check --deploy

# Collect static files (if any)
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build completed successfully!"
echo "🎯 Ready for deployment on Render"