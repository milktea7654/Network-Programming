#!/bin/bash
# 啟動 Database Server 和 Lobby Server（在課程機上執行）

echo "Starting Database Server..."
python3 db_server.py &
DB_PID=$!

sleep 2

echo "Starting Lobby Server..."
python3 lobby_server.py &
LOBBY_PID=$!

echo ""
echo "=========================================="
echo "Servers are running:"
echo "  Database Server (PID: $DB_PID) on port 10001"
echo "  Lobby Server (PID: $LOBBY_PID) on port 10002"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# 等待中斷信號
trap "kill $DB_PID $LOBBY_PID 2>/dev/null; echo 'Servers stopped'; exit" INT

wait
