#!/bin/bash
# 測試腳本：啟動兩個客戶端進行測試

if [ -z "$1" ]; then
    echo "Usage: ./test_game.sh <server_ip>"
    exit 1
fi

SERVER_IP=$1

echo "Opening two lobby clients..."
echo ""
echo "Terminal 1: Player 1"
gnome-terminal -- bash -c "python3 lobby_client.py $SERVER_IP 10002; exec bash"

sleep 1

echo "Terminal 2: Player 2"
gnome-terminal -- bash -c "python3 lobby_client.py $SERVER_IP 10002; exec bash"

echo ""
echo "Two clients launched. Please:"
echo "1. Register/Login in both clients"
echo "2. Player 1: Create a room"
echo "3. Player 2: Join the room"
echo "4. Player 1: Start game"
