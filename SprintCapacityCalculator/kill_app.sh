#!/bin/bash
# Kill Sprint Capacity Calculator processes
# Run this if the app gets stuck or won't stop

echo "🛑 Stopping Sprint Capacity Calculator..."

# Kill by port (safest method)
echo "🔍 Looking for processes on port 5001..."
PIDS=$(lsof -ti:5001 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    echo "💀 Killing processes on port 5001: $PIDS"
    echo $PIDS | xargs kill -9
    echo "✅ Processes killed"
else
    echo "ℹ️  No processes found on port 5001"
fi

# Kill by process name (backup method)
echo "🔍 Looking for Flask/Python processes..."
FLASK_PIDS=$(pgrep -f "python.*app.py" 2>/dev/null)
RUN_PIDS=$(pgrep -f "python.*run.py" 2>/dev/null)

if [ ! -z "$FLASK_PIDS" ]; then
    echo "💀 Killing Flask processes: $FLASK_PIDS"
    echo $FLASK_PIDS | xargs kill -9
fi

if [ ! -z "$RUN_PIDS" ]; then
    echo "💀 Killing run.py processes: $RUN_PIDS"
    echo $RUN_PIDS | xargs kill -9
fi

echo "🎉 Cleanup complete!"
echo "💡 You can now start the app again with: python3 run.py" 