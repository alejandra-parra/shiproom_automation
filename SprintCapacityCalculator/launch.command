#!/bin/bash
# Sprint Capacity Calculator - macOS Launch Script
# Double-click this file to start the application

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "🚀 Starting Sprint Capacity Calculator..."
echo "📁 Working directory: $DIR"

# Run the application
python3 run.py

# Keep terminal open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application failed to start. Press any key to close..."
    read -n 1
fi 