import argparse
import json
import socket
import threading
import time
from common import JsonLineSocket, send_json_line, recv_json_line, bind_with_retry
from connect4 import Connect4
from time import sleep
ENC = 'utf-8'

class LobbyClient:
    def __init__(self, host, port, username, password):
        self.addr = (host, port)
        self.u = username
        self.p = password

    def _rpc(self, obj):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.addr)
        js = JsonLineSocket(s)
        js.send(obj)
        resp = js.recv()
        s.close()
        return resp

    def register(self):
        return self._rpc({"type":"REGISTER","username":self.u,"password":self.p})

    def login(self):
        return self._rpc({"type":"LOGIN","username":self.u,"password":self.p})

    def report(self, delta):
        return self._rpc({"type":"REPORT","username":self.u,"delta":delta})

    def logout(self):
        return self._rpc({"type":"LOGOUT","username":self.u})


def udp_discover(hosts, pstart, pend, timeout=0.2):
    results = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    probe = json.dumps({"type":"DISCOVER"}).encode(ENC)
    for h in hosts:
        for port in range(pstart, pend+1):
            try:
                sock.sendto(probe, (h, port))
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode(ENC))
                if msg.get('type') == 'HERE' and msg.get('status') == 'waiting':
                    results.append({**msg, 'addr': addr})
            except socket.timeout:
                pass
            except Exception:
                pass
    return results


def display_board(game_state):
    """顯示棋盤給 Player A"""
    board = game_state['board']
    turn = game_state['turn']
    winner = game_state['winner']
    
    print("\n" + "="*29)
    print("         四子棋遊戲棋盤")
    print("="*29)
    print("  0 1 2 3 4 5 6")
    for i, row in enumerate(board):
        print(f"{i} " + " ".join(str(cell) for cell in row))
    print("="*29)
    print(f"輪到：{turn}  勝負：{winner if winner else '進行中'}")
    if turn == 'A':
        print("💡 輪到您下棋了！")
    else:
        print("⏳ 等待對手下棋...")
    print("="*29)

def game_server_thread(listen_sock, a_username, lobby: LobbyClient):
    conn, addr = listen_sock.accept()
    js = JsonLineSocket(conn)
    g = Connect4()

    js.send({"type":"HELLO","as":"A","game":"connect4"})
    peer = js.recv()
    
    print(f"🎮 遊戲開始！您是 Player A (棋子顯示為 '1')")
    print(f"🤝 對手 Player B 已連接 (棋子顯示為 '2')")

    try:
        broadcast = lambda: js.send({"type":"STATE", **g.copy_state()})
    
        display_board(g.copy_state())
        broadcast()
        
        while g.winner is None:
            if g.turn == 'A':
                col = input("[A] 請輸入欄位(0-6)：").strip()
                try:
                    col = int(col)
                    g.drop(col)
                    display_board(g.copy_state())
                except Exception as e:
                    print("❌ 非法輸入：", e)
                    continue
                broadcast()
            else:
                msg = js.recv()
                if msg is None:
                    print("💔 對手離線")
                    break
                if msg.get('type') == 'MOVE':
                    try:
                        opponent_col = int(msg.get('col'))
                        print(f"🔵 對手在第 {opponent_col} 列下棋")
                        g.drop(opponent_col)
                        display_board(g.copy_state())
                        broadcast()
                    except Exception as e:
                        js.send({"type":"ERROR","msg":str(e)})
                else:
                    js.send({"type":"ERROR","msg":"EXPECT_MOVE"})
        if g.winner:
            print("\n🎉 遊戲結束！")
            display_board(g.copy_state())
            if g.winner == 'A':
                print("🏆 恭喜！您獲勝了！")
                lobby.report({"wins": 1})
            elif g.winner == 'B':
                print("😔 很遺憾，您輸了...")
                lobby.report({"loses": 1})
            elif g.winner == 'draw':
                print("🤝 平局！")
        else:
            print("⚠️ 遊戲被中斷")
    finally:
        try: js.send({"type":"BYE"})
        except Exception: pass
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lobby-host', required=True)
    ap.add_argument('--lobby-port', type=int, default=12000)
    ap.add_argument('--username', required=True)
    ap.add_argument('--password', required=True)
    ap.add_argument('--scan-hosts', nargs='+', required=True)
    ap.add_argument('--scan-port-start', type=int, default=18000)
    ap.add_argument('--scan-port-end', type=int, default=18020)
    ap.add_argument('--game-tcp-port', type=int, default=19000)
    args = ap.parse_args()

    lobby = LobbyClient(args.lobby_host, args.lobby_port, args.username, args.password)
    r = lobby.register()
    if not r.get('ok') and r.get('msg') != 'USER_EXISTS':
        print('[A] register fail:', r)
    r = lobby.login()
    if not r.get('ok'):
        print('[A] login fail:', r)
        return
    print('[A] login success')

    avail = udp_discover(args.scan_hosts, args.scan_port_start, args.scan_port_end)
    if not avail:
        print('[A] 找不到等待中的玩家B')
        lobby.logout()
        return
    target = avail[0]
    print('[A] 選擇目標：', target)

    us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    us.settimeout(15)
    us.sendto(json.dumps({"type":"INVITE","from":args.username}).encode(ENC), target['addr'])
    data, _ = us.recvfrom(1024)
    rep = json.loads(data.decode(ENC))
    
    if not (rep.get('type') == 'INVITE_REPLY' and rep.get('accept') is True):
        print('[A] 被拒絕或異常')
        lobby.logout()
        return
    lsock, bound_port = bind_with_retry('0.0.0.0', args.game_tcp_port)
    print(f'[A] 遊戲伺服器綁定於 TCP {bound_port}')

    try:
        import socket as sock_module
        hostname = sock_module.gethostname()
        if 'linux' in hostname and 'cs.nycu.edu.tw' not in hostname:
            external_ip = f"{hostname}.cs.nycu.edu.tw"
        else:
            external_ip = hostname
        print(f'[A] 使用主機名: {external_ip}')
    except:
        external_ip = socket.gethostbyname(socket.gethostname())
        print(f'[A] 使用 IP: {external_ip}')
    
    us.sendto(json.dumps({"type":"TCP_INFO","host":external_ip,
                          "port": bound_port}).encode(ENC), target['addr'])

    t = threading.Thread(target=game_server_thread, args=(lsock, args.username, lobby), daemon=True)
    t.start()

    t.join()
    lobby.logout()

if __name__ == '__main__':
    main()