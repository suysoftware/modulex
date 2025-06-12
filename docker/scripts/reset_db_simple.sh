#!/bin/bash
echo "🗄️ Resetting database completely..."

# Stop and remove everything 
docker-compose down -v

echo "✅ Database volume removed"

# Start fresh
docker-compose up -d

echo "⏳ Waiting for services..."
sleep 20

echo "✅ Database reset complete! Application starting..." 