import json
import socket
import sys
import time

ENC = "utf-8"

def send_json_line(conn, obj):
    data = json.dumps(obj, separators=(",", ":")).encode(ENC) + b"\n"
    conn.sendall(data)

def recv_json_line(conn):
    buf = b""
    while True:
        ch = conn.recv(1)
        if not ch:
            if buf:
                raise ConnectionError("connection closed mid-line")
            return None
        if ch == b"\n":
            break
        buf += ch
    return json.loads(buf.decode(ENC))

class JsonLineSocket:
    def __init__(self, sock):
        self.sock = sock
        self.sock.settimeout(30)
        self.file = self.sock.makefile("rwb", buffering=0)

    def send(self, obj):
        data = json.dumps(obj, separators=(",", ":")).encode(ENC) + b"\n"
        self.file.write(data)

    def recv(self):
        line = self.file.readline()
        if not line:
            return None
        return json.loads(line.decode(ENC))


def bind_with_retry(host, port, max_tries=10):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(max_tries):
        try:
            s.bind((host, port))
            s.listen(5)
            return s, port
        except OSError as e:
            if e.errno in (98, 48): 
                port += 1
                time.sleep(0.1)
            else:
                raise
    raise OSError("cannot bind after retries")