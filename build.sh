#!/bin/bash
# Build script for Heroku deployment

echo "Building React frontend..."
cd frontend
npm install
npm run build
cd ..
echo "Frontend build complete!"
