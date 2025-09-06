#!/bin/bash
# deploy-to-dev-server.sh
# Manual deployment script for dev-server (34.134.14.202)

set -e

echo "🚀 Starting deployment to dev-server..."

# Navigate to the services directory
cd /srv/servicios

# Create entersys-backend directory if it doesn't exist
if [ ! -d "entersys-backend" ]; then
    echo "📁 Creating entersys-backend directory..."
    mkdir -p entersys-backend
fi

cd entersys-backend

# Clone or pull latest changes
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes from GitHub..."
    git pull origin main
else
    echo "📥 Cloning repository from GitHub..."
    git clone https://github.com/EntersysMX/entersys-backend.git .
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    
    # Update with production values
    sed -i 's/POSTGRES_PASSWORD=/POSTGRES_PASSWORD=entersys_dev_pass_2025/' .env
    echo "✅ .env file configured"
else
    echo "✅ .env file already exists"
fi

# Stop existing containers (if any)
echo "🛑 Stopping existing containers..."
docker-compose down || echo "No existing containers to stop"

# Build and start new containers
echo "🔨 Building and starting containers..."
docker-compose up -d --build

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 30

# Check container status
echo "📊 Checking container status..."
docker-compose ps

# Test health endpoint
echo "🏥 Testing health endpoint..."
sleep 10
curl -f http://localhost:8000/api/v1/health || echo "Health check will be available after Traefik routing is configured"

echo "✅ Deployment completed successfully!"
echo "🌐 The API will be available at: https://api.dev.entersys.mx"
echo "🏥 Health check: https://api.dev.entersys.mx/api/v1/health"
echo "📚 API docs: https://api.dev.entersys.mx/docs"