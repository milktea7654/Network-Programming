import argparse
import json
import os
import socket
import threading
from common import JsonLineSocket

USERS_FILE = 'users.json'
STATS_FILE = 'stats.json'

lock = threading.Lock()

users = {}       
online = set()   
stats = {}     


def load_persist():
    global users, stats
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)


def save_persist():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f)
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f)


def ensure_user_stats(u):
    if u not in stats:
        stats[u] = {"wins": 0, "loses": 0, "logins": 0}
    if "logins" not in stats[u]:
        stats[u]["logins"] = 0


def handle_client(conn, addr):
    js = JsonLineSocket(conn)
    username = None
    try:
        while True:
            msg = js.recv()
            if msg is None:
                break
            t = msg.get('type')

            if t == 'REGISTER':
                u, p = msg.get('username'), msg.get('password')
                if not u or not p:
                    js.send({"ok": False, "msg": "INVALID_INPUT"})
                    continue
                with lock:
                    if u in users:
                        js.send({"ok": False, "msg": "USER_EXISTS"})
                    else:
                        users[u] = p
                        ensure_user_stats(u)
                        save_persist()
                        js.send({"ok": True, "msg": "REGISTER_SUCCESS"})

            elif t == 'LOGIN':
                u, p = msg.get('username'), msg.get('password')
                with lock:
                    if u not in users or users[u] != p:
                        js.send({"ok": False, "msg": "LOGIN_FAIL"})
                    elif u in online:
                        js.send({"ok": False, "msg": "DUPLICATE_LOGIN"})
                    else:
                        online.add(u)
                        ensure_user_stats(u)
                        stats[u]['logins'] += 1
                        save_persist()
                        username = u
                        js.send({"ok": True, "msg": "LOGIN_SUCCESS"})

            elif t == 'REPORT':
                u = msg.get('username')
                delta = msg.get('delta', {})
                with lock:
                    ensure_user_stats(u)
                    for k, v in delta.items():
                        stats[u][k] = stats[u].get(k, 0) + int(v)
                    save_persist()
                js.send({"ok": True, "msg": "REPORT_OK"})

            elif t == 'LOGOUT':
                u = msg.get('username')
                with lock:
                    if u in online:
                        online.remove(u)
                        save_persist()
                js.send({"ok": True, "msg": "LOGOUT_OK"})
                break

            else:
                js.send({"ok": False, "msg": "UNKNOWN_TYPE"})

    except Exception as e:
        try:
            js.send({"ok": False, "msg": f"SERVER_ERROR:{e}"})
        except Exception:
            pass
    finally:
        if username:
            with lock:
                if username in online:
                    online.remove(username)
                    save_persist()
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=12000)
    args = ap.parse_args()

    load_persist()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((args.host, args.port))
    s.listen(100)
    print(f"[lobby] listening on {args.host}:{args.port}")

    while True:
        c, addr = s.accept()
        threading.Thread(target=handle_client, args=(c, addr), daemon=True).start()

if __name__ == '__main__':
    main()