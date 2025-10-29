"""
Database Server - 獨立的資料庫服務
使用 TCP + JSON API，底層使用 SQLite
"""
import socket
import sqlite3
import threading
import json
from datetime import datetime
from protocol import send_message, recv_message, ProtocolError
import hashlib

DB_HOST = '0.0.0.0'
DB_PORT = 10001
DB_FILE = 'game_database.db'


class DatabaseServer:
    def __init__(self, host=DB_HOST, port=DB_PORT):
        self.host = host
        self.port = port
        self.running = False
        self.init_database()
        
    def init_database(self):
        """初始化資料庫結構"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # User 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS User (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                passwordHash TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                lastLoginAt TEXT
            )
        ''')
        
        # Room 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Room (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hostUserId INTEGER NOT NULL,
                visibility TEXT NOT NULL,
                inviteList TEXT,
                status TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                FOREIGN KEY (hostUserId) REFERENCES User(id)
            )
        ''')
        
        # GameLog 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS GameLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matchId TEXT NOT NULL,
                roomId INTEGER NOT NULL,
                users TEXT NOT NULL,
                startAt TEXT NOT NULL,
                endAt TEXT,
                results TEXT,
                FOREIGN KEY (roomId) REFERENCES Room(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"[DB] Database initialized: {DB_FILE}")
    
    def start(self):
        """啟動資料庫伺服器"""
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        
        print(f"[DB Server] Listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    print(f"[DB] New connection from {addr}")
                    
                    # 為每個連接創建新線程
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n[DB Server] Shutting down...")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, addr):
        """處理客戶端請求"""
        try:
            while True:
                # 接收請求
                request = recv_message(client_socket)
                print(f"[DB] Request from {addr}: {request.get('action')} on {request.get('collection')}")
                
                # 處理請求
                response = self.process_request(request)
                
                # 發送回應
                send_message(client_socket, response)
                
        except (ConnectionError, ProtocolError) as e:
            print(f"[DB] Connection error from {addr}: {e}")
        except Exception as e:
            print(f"[DB] Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            print(f"[DB] Connection closed: {addr}")
    
    def process_request(self, request):
        """處理資料庫請求"""
        collection = request.get('collection')
        action = request.get('action')
        data = request.get('data', {})
        
        try:
            if action == 'create':
                return self.create(collection, data)
            elif action == 'read':
                return self.read(collection, data)
            elif action == 'update':
                return self.update(collection, data)
            elif action == 'delete':
                return self.delete(collection, data)
            elif action == 'query':
                return self.query(collection, data)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create(self, collection, data):
        """創建記錄"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            if collection == 'User':
                cursor.execute('''
                    INSERT INTO User (name, email, passwordHash, createdAt)
                    VALUES (?, ?, ?, ?)
                ''', (data['name'], data['email'], data['passwordHash'], 
                      datetime.now().isoformat()))
                user_id = cursor.lastrowid
                conn.commit()
                return {'success': True, 'id': user_id}
                
            elif collection == 'Room':
                cursor.execute('''
                    INSERT INTO Room (name, hostUserId, visibility, inviteList, status, createdAt)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (data['name'], data['hostUserId'], data['visibility'],
                      json.dumps(data.get('inviteList', [])), 'idle',
                      datetime.now().isoformat()))
                room_id = cursor.lastrowid
                conn.commit()
                return {'success': True, 'id': room_id}
                
            elif collection == 'GameLog':
                cursor.execute('''
                    INSERT INTO GameLog (matchId, roomId, users, startAt, endAt, results)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (data['matchId'], data['roomId'], json.dumps(data['users']),
                      data['startAt'], data.get('endAt'), json.dumps(data.get('results', []))))
                log_id = cursor.lastrowid
                conn.commit()
                return {'success': True, 'id': log_id}
            else:
                return {'success': False, 'error': f'Unknown collection: {collection}'}
        finally:
            conn.close()
    
    def read(self, collection, data):
        """讀取記錄"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            record_id = data.get('id')
            if collection == 'User':
                cursor.execute('SELECT * FROM User WHERE id = ?', (record_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'success': True,
                        'data': {
                            'id': row[0], 'name': row[1], 'email': row[2],
                            'passwordHash': row[3], 'createdAt': row[4], 'lastLoginAt': row[5]
                        }
                    }
                else:
                    return {'success': False, 'error': 'User not found'}
                    
            elif collection == 'Room':
                cursor.execute('SELECT * FROM Room WHERE id = ?', (record_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'success': True,
                        'data': {
                            'id': row[0], 'name': row[1], 'hostUserId': row[2],
                            'visibility': row[3], 'inviteList': json.loads(row[4]),
                            'status': row[5], 'createdAt': row[6]
                        }
                    }
                else:
                    return {'success': False, 'error': 'Room not found'}
            else:
                return {'success': False, 'error': f'Unknown collection: {collection}'}
        finally:
            conn.close()
    
    def update(self, collection, data):
        """更新記錄"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            record_id = data.get('id')
            updates = data.get('updates', {})
            
            if collection == 'User':
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [record_id]
                cursor.execute(f'UPDATE User SET {set_clause} WHERE id = ?', values)
            elif collection == 'Room':
                # 特殊處理 inviteList（需要序列化）
                if 'inviteList' in updates:
                    updates['inviteList'] = json.dumps(updates['inviteList'])
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [record_id]
                cursor.execute(f'UPDATE Room SET {set_clause} WHERE id = ?', values)
            elif collection == 'GameLog':
                if 'users' in updates:
                    updates['users'] = json.dumps(updates['users'])
                if 'results' in updates:
                    updates['results'] = json.dumps(updates['results'])
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [record_id]
                cursor.execute(f'UPDATE GameLog SET {set_clause} WHERE id = ?', values)
            else:
                return {'success': False, 'error': f'Unknown collection: {collection}'}
            
            conn.commit()
            return {'success': True, 'modified': cursor.rowcount}
        finally:
            conn.close()
    
    def delete(self, collection, data):
        """刪除記錄"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            record_id = data.get('id')
            cursor.execute(f'DELETE FROM {collection} WHERE id = ?', (record_id,))
            conn.commit()
            return {'success': True, 'deleted': cursor.rowcount}
        finally:
            conn.close()
    
    def query(self, collection, data):
        """查詢記錄"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            if collection == 'User':
                # 支援按名稱或 email 查詢
                if 'name' in data:
                    cursor.execute('SELECT * FROM User WHERE name = ?', (data['name'],))
                elif 'email' in data:
                    cursor.execute('SELECT * FROM User WHERE email = ?', (data['email'],))
                else:
                    cursor.execute('SELECT * FROM User')
                
                rows = cursor.fetchall()
                users = [{
                    'id': r[0], 'name': r[1], 'email': r[2],
                    'passwordHash': r[3], 'createdAt': r[4], 'lastLoginAt': r[5]
                } for r in rows]
                return {'success': True, 'data': users}
                
            elif collection == 'Room':
                # 支援按狀態或可見性查詢
                if 'status' in data:
                    cursor.execute('SELECT * FROM Room WHERE status = ?', (data['status'],))
                elif 'visibility' in data:
                    cursor.execute('SELECT * FROM Room WHERE visibility = ?', (data['visibility'],))
                else:
                    cursor.execute('SELECT * FROM Room')
                
                rows = cursor.fetchall()
                rooms = [{
                    'id': r[0], 'name': r[1], 'hostUserId': r[2],
                    'visibility': r[3], 'inviteList': json.loads(r[4]),
                    'status': r[5], 'createdAt': r[6]
                } for r in rows]
                return {'success': True, 'data': rooms}
                
            elif collection == 'GameLog':
                if 'roomId' in data:
                    cursor.execute('SELECT * FROM GameLog WHERE roomId = ?', (data['roomId'],))
                else:
                    cursor.execute('SELECT * FROM GameLog')
                
                rows = cursor.fetchall()
                logs = [{
                    'id': r[0], 'matchId': r[1], 'roomId': r[2],
                    'users': json.loads(r[3]), 'startAt': r[4],
                    'endAt': r[5], 'results': json.loads(r[6]) if r[6] else []
                } for r in rows]
                return {'success': True, 'data': logs}
            else:
                return {'success': False, 'error': f'Unknown collection: {collection}'}
        finally:
            conn.close()


def hash_password(password):
    """密碼雜湊"""
    return hashlib.sha256(password.encode()).hexdigest()


if __name__ == '__main__':
    server = DatabaseServer()
    server.start()
