#!/bin/bash

# Exit on error
set -e

echo "==== CIS Benchmark Parser Setup Script ===="
echo ""

# Determine OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="MacOS"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32" ]]; then
  OS="Windows"
else
  OS="Unknown"
fi

echo "Detected OS: $OS"
echo ""

# Check for Docker
if command -v docker &> /dev/null; then
  echo "✓ Docker is installed"
else
  echo "✗ Docker is not installed"
  echo "  Please install Docker first: https://www.docker.com/get-started"
  exit 1
fi

# Check for Docker Compose
if command -v docker-compose &> /dev/null; then
  echo "✓ Docker Compose is installed"
else
  echo "✗ Docker Compose is not installed"
  echo "  Please install Docker Compose first: https://docs.docker.com/compose/install/"
  exit 1
fi

echo ""
echo "All requirements are satisfied!"
echo ""

# Ask user if they want to build and run the application
read -p "Do you want to build and run the application now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "Building and starting the application..."
  echo ""
  
  # Build and run with Docker Compose
  docker-compose up -d --build
  
  echo ""
  echo "Application is running!"
  echo "- Frontend: http://localhost"
  echo "- Backend API: http://localhost:8000"
  echo ""
  echo "You can view logs with: docker-compose logs -f"
  echo "Stop the application with: docker-compose down"
else
  echo ""
  echo "Setup completed. You can run the application later with:"
  echo "  docker-compose up -d"
fi