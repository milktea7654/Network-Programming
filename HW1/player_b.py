import argparse
import json
import socket
import threading
from common import JsonLineSocket
from connect4 import Connect4

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


def udp_wait_loop(udp_port, auto_accept):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', udp_port))
    print(f'[B] UDP waiting on {udp_port}')

    tcp_info = None
    inviter = None

    while True:
        data, addr = s.recvfrom(2048)
        try:
            msg = json.loads(data.decode(ENC))
        except Exception:
            continue

        t = msg.get('type')
        if t == 'DISCOVER':
            resp = {"type":"HERE","username":"?","udp_port":udp_port,"status":"waiting"}
            s.sendto(json.dumps(resp).encode(ENC), addr)
        elif t == 'INVITE':
            inviter = msg.get('from')
            if auto_accept:
                s.sendto(json.dumps({"type":"INVITE_REPLY","accept":True}).encode(ENC), addr)
            else:
                ans = input(f"收到 {inviter} 邀請，接受？(y/n) ").strip().lower()
                s.sendto(json.dumps({"type":"INVITE_REPLY","accept": ans.startswith('y')}).encode(ENC), addr)
        elif t == 'TCP_INFO':
            tcp_info = (msg.get('host'), int(msg.get('port')))
            return tcp_info, inviter


def play_as_client(host, port, lobby: LobbyClient):
    s = socket.create_connection((host, port))
    js = JsonLineSocket(s)
    hello = js.recv()
    js.send({"type":"HELLO","as":"B","game":"connect4"})

    gstate = None
    try:
        while True:
            msg = js.recv()
            if msg is None:
                print('[B] 連線中斷')
                break
            if msg.get('type') == 'STATE':
                gstate = msg
                board = gstate['board']
                turn = gstate['turn']
                winner = gstate['winner']
                print("\n".join(" ".join(str(c) for c in row) for row in board))
                print(f"輪到：{turn}  勝負：{winner}")
                if winner:
                    if winner == 'B':
                        lobby.report({"wins": 1})
                    elif winner == 'A':
                        lobby.report({"loses": 1})
                    break
                if turn == 'B':
                    try:
                        col = int(input('[B] 請輸入欄位(0-6)：').strip())
                        js.send({"type":"MOVE","col":col})
                    except Exception:
                        js.send({"type":"MOVE","col":-1})
            elif msg.get('type') == 'ERROR':
                print('[B] 錯誤：', msg.get('msg'))
            elif msg.get('type') == 'BYE':
                break
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lobby-host', required=True)
    ap.add_argument('--lobby-port', type=int, default=12000)
    ap.add_argument('--username', required=True)
    ap.add_argument('--password', required=True)
    ap.add_argument('--udp-port', type=int, required=True)
    ap.add_argument('--auto-accept', action='store_true')
    args = ap.parse_args()

    lobby = LobbyClient(args.lobby_host, args.lobby_port, args.username, args.password)
    r = lobby.register()
    if not r.get('ok') and r.get('msg') != 'USER_EXISTS':
        print('[B] register fail:', r)
    r = lobby.login()
    if not r.get('ok'):
        print('[B] login fail:', r)
        return

    tcp_info, inviter = udp_wait_loop(args.udp_port, args.auto_accept)
    print('[B] 接收連線資訊：', tcp_info)

    try:
        play_as_client(tcp_info[0], tcp_info[1], lobby)
    finally:
        lobby.logout()

if __name__ == '__main__':
    main()