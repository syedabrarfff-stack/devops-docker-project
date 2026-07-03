#!/bin/bash
# Local development startup — runs backend + frontend

set -e

echo "🚀 Starting JARVIS Dashboard..."
echo ""

# Kill any existing processes
killall uvicorn 2>/dev/null || true
killall node 2>/dev/null || true
sleep 1

# Backend
echo "Starting backend (FastAPI)..."
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > /tmp/jarvis-backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
sleep 2

# Frontend
echo "Starting frontend (Vite)..."
cd ../frontend
npm run dev > /tmp/jarvis-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
sleep 3

echo ""
echo "✅ JARVIS Dashboard is LIVE"
echo ""
echo "  Dashboard:  http://localhost:3000"
echo "  Backend:    http://localhost:8000"
echo "  Health:     http://localhost:8000/health"
echo ""
echo "  Backend logs:  tail -f /tmp/jarvis-backend.log"
echo "  Frontend logs: tail -f /tmp/jarvis-frontend.log"
echo ""
echo "Press CTRL+C to stop"

# Wait for signals
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped'; exit 0" SIGINT SIGTERM
wait
