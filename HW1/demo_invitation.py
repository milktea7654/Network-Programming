#!/usr/bin/env python3
"""
遊戲邀請（Game Invitation）完整流程演示
根據架構圖展示完整的UDP通訊邀請機制
"""
import socket
import json
import threading
import time
import sys

ENC = 'utf-8'

def demonstrate_invitation_flow():
    print("=" * 60)
    print("           遊戲邀請（Game Invitation）完整流程演示")
    print("=" * 60)
    
    print("\n🎯 根據架構圖，邀請流程包含以下步驟：")
    print("1. Player A 掃描尋找等待中的 Player B")
    print("2. Player A 發送遊戲邀請給 Player B") 
    print("3. Player B 接受邀請")
    print("4. Player A 發送 TCP 連線資訊給 Player B")
    print("5. Player B 連接到 Player A 的遊戲伺服器")
    
    print(f"\n📡 Step 1: 啟動 Player B 等待模式...")
    
    def mock_player_b():
        """模擬 Player B 的等待和回應邏輯"""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('0.0.0.0', 18000))
        print(f"   [Player B] 在 UDP 18000 等待邀請...")
        
        tcp_info = None
        inviter = None
        
        while True:
            try:
                data, addr = udp_socket.recvfrom(2048)
                msg = json.loads(data.decode(ENC))
                msg_type = msg.get('type')
                
                if msg_type == 'DISCOVER':
                    resp = {
                        "type": "HERE",
                        "username": "demo_player_b", 
                        "udp_port": 18000,
                        "status": "waiting"
                    }
                    udp_socket.sendto(json.dumps(resp).encode(ENC), addr)
                    print(f"   [Player B] 回應發現請求來自 {addr}")
                    
                elif msg_type == 'INVITE':
                    inviter = msg.get('from', 'unknown')
                    print(f"   [Player B] 收到來自 {inviter} 的邀請")
                    reply = {
                        "type": "INVITE_REPLY",
                        "accept": True
                    }
                    udp_socket.sendto(json.dumps(reply).encode(ENC), addr)
                    print(f"   [Player B] 已接受 {inviter} 的邀請")
                    
                elif msg_type == 'TCP_INFO':
                    tcp_info = (msg.get('host'), int(msg.get('port')))
                    print(f"   [Player B] 收到 TCP 連線資訊: {tcp_info}")
                    udp_socket.close()
                    return tcp_info, inviter
                    
            except Exception as e:
                print(f"   [Player B] 錯誤: {e}")
                break
        
        udp_socket.close()
        return None, None

    b_thread = threading.Thread(target=mock_player_b, daemon=True)
    b_thread.start()
    time.sleep(0.5) 
    print(f"\n🔍 Step 2: Player A 開始掃描...")
    
    def player_a_invitation_flow():
        """模擬 Player A 的邀請流程"""
        print(f"   [Player A] 掃描 127.0.0.1:18000-18005...")
        
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(1)
        
        discover_msg = json.dumps({"type": "DISCOVER"}).encode(ENC)
        found_players = []
        
        for port in range(18000, 18006):
            try:
                udp_socket.sendto(discover_msg, ('127.0.0.1', port))
                data, addr = udp_socket.recvfrom(1024)
                response = json.loads(data.decode(ENC))
                
                if response.get('type') == 'HERE' and response.get('status') == 'waiting':
                    found_players.append({**response, 'addr': addr})
                    print(f"   [Player A] 發現等待中的玩家: {response['username']} at {addr}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                continue
        
        if not found_players:
            print(f"   [Player A] ❌ 未發現等待中的玩家")
            return False
            
        target = found_players[0]
        print(f"\n💌 Step 3: Player A 發送邀請給 {target['username']}...")
        
        invite_msg = json.dumps({
            "type": "INVITE",
            "from": "demo_player_a"
        }).encode(ENC)
        
        udp_socket.sendto(invite_msg, target['addr'])
        print(f"   [Player A] 已發送邀請到 {target['addr']}")
        try:
            data, addr = udp_socket.recvfrom(1024)
            invite_reply = json.loads(data.decode(ENC))
            
            if invite_reply.get('type') == 'INVITE_REPLY' and invite_reply.get('accept'):
                print(f"   [Player A] ✅ 邀請被接受！")
                print(f"\n🎮 Step 4: Player A 建立 TCP 遊戲伺服器...")
                tcp_port = 19000
                print(f"   [Player A] TCP 遊戲伺服器綁定於 127.0.0.1:{tcp_port}")
                print(f"\n📡 Step 5: Player A 發送 TCP 資訊給 Player B...")
                
                tcp_info_msg = json.dumps({
                    "type": "TCP_INFO",
                    "host": "127.0.0.1",
                    "port": tcp_port
                }).encode(ENC)
                
                udp_socket.sendto(tcp_info_msg, target['addr'])
                print(f"   [Player A] 已發送 TCP 連線資訊: 127.0.0.1:{tcp_port}")
                
                return True
                
            else:
                print(f"   [Player A] ❌ 邀請被拒絕")
                return False
                
        except socket.timeout:
            print(f"   [Player A] ❌ 邀請回應超時")
            return False
            
        finally:
            udp_socket.close()
    success = player_a_invitation_flow()
    
    time.sleep(1) 
    
    print(f"\n📋 流程總結:")
    if success:
        print(f"   ✅ UDP 發現協議 - Player A 成功找到 Player B")
        print(f"   ✅ UDP 邀請協議 - 邀請發送和接受成功")
        print(f"   ✅ TCP 資訊交換 - 遊戲連線資訊已傳送")
        print(f"   🎮 準備開始遊戲 - Player B 可以連接到 Player A")
    else:
        print(f"   ❌ 邀請流程失敗")
    
    print(f"\n" + "=" * 60)
    print(f"邀請流程演示完成！")
    print(f"=" * 60)

def show_code_walkthrough():
    """展示實際程式碼的關鍵部分"""
    print(f"\n🔧 實際程式碼關鍵部分:")
    
    print(f"\n1. Player A 掃描功能 (player_a.py):")
    print(f"""
def udp_discover(hosts, pstart, pend, timeout=0.2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe = json.dumps({{"type":"DISCOVER"}}).encode(ENC)
    for h in hosts:
        for port in range(pstart, pend+1):
            sock.sendto(probe, (h, port))
            data, addr = sock.recvfrom(1024)
            # 處理回應...
    """)
    
    print(f"\n2. Player B 等待功能 (player_b.py):")
    print(f"""
def udp_wait_loop(udp_port, auto_accept):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', udp_port))
    while True:
        data, addr = s.recvfrom(2048)
        msg = json.loads(data.decode(ENC))
        
        if msg.get('type') == 'DISCOVER':
            # 回應發現請求
        elif msg.get('type') == 'INVITE':  
            # 處理邀請
        elif msg.get('type') == 'TCP_INFO':
            # 接收遊戲連線資訊
    """)

if __name__ == "__main__":
    demonstrate_invitation_flow()
    show_code_walkthrough()