#!/usr/bin/env python3
"""
數據持久化管理器
負責將數據保存到文件系統，確保Server重啟後數據不丟失
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from models import User, Game, Room, PlayerGameRecord

class DataManager:
    """數據管理器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # 數據文件路徑
        self.users_file = os.path.join(data_dir, "users.json")
        self.games_file = os.path.join(data_dir, "games.json")
        self.rooms_file = os.path.join(data_dir, "rooms.json")
        self.records_file = os.path.join(data_dir, "game_records.json")
        
        # 內存中的數據
        self.users = {}  # {username: User}
        self.games = {}  # {game_name: Game}
        self.rooms = {}  # {room_id: Room}
        self.game_records = []  # [PlayerGameRecord]
        
        # 加載現有數據
        self.load_data()
    
    def load_data(self):
        """從文件加載數據"""
        try:
            # 加載用戶數據
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    for username, data in users_data.items():
                        self.users[username] = User.from_dict(data)
            
            # 加載遊戲數據
            if os.path.exists(self.games_file):
                with open(self.games_file, 'r', encoding='utf-8') as f:
                    games_data = json.load(f)
                    for game_name, data in games_data.items():
                        self.games[game_name] = Game.from_dict(data)
            
            # 加載房間數據（通常重啟後清空）
            if os.path.exists(self.rooms_file):
                with open(self.rooms_file, 'r', encoding='utf-8') as f:
                    rooms_data = json.load(f)
                    for room_id, data in rooms_data.items():
                        self.rooms[room_id] = Room.from_dict(data)
            
            # 加載遊戲記錄
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    records_data = json.load(f)
                    for data in records_data:
                        self.game_records.append(PlayerGameRecord.from_dict(data))
                        
            print(f"數據加載完成: {len(self.users)} 用戶, {len(self.games)} 遊戲, {len(self.rooms)} 房間")
            
        except Exception as e:
            print(f"加載數據時出錯: {e}")
    
    def save_data(self):
        """保存所有數據到文件"""
        try:
            # 保存用戶數據
            users_data = {username: user.to_dict() for username, user in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            
            # 保存遊戲數據
            games_data = {name: game.to_dict() for name, game in self.games.items()}
            with open(self.games_file, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, ensure_ascii=False, indent=2)
            
            # 保存房間數據
            rooms_data = {room_id: room.to_dict() for room_id, room in self.rooms.items()}
            with open(self.rooms_file, 'w', encoding='utf-8') as f:
                json.dump(rooms_data, f, ensure_ascii=False, indent=2)
            
            # 保存遊戲記錄
            records_data = [record.to_dict() for record in self.game_records]
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(records_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存數據時出錯: {e}")
    
    # 用戶管理
    def create_user(self, username: str, password: str, user_type: str) -> bool:
        """創建用戶"""
        if username in self.users:
            return False
        self.users[username] = User(username, password, user_type)
        self.save_data()
        return True
    
    def authenticate_user(self, username: str, password: str, user_type: str) -> Optional[User]:
        """用戶登入驗證"""
        if username in self.users:
            user = self.users[username]
            if user.password == password and user.user_type == user_type:
                return user
        return None
    
    def set_user_online(self, username: str, status: bool):
        """設置用戶在線狀態"""
        if username in self.users:
            self.users[username].is_online = status
            if status:
                self.users[username].last_login = datetime.now()
            self.save_data()
    
    def get_online_users(self, user_type: str = None) -> List[User]:
        """獲取在線用戶"""
        users = []
        for user in self.users.values():
            if user.is_online and (user_type is None or user.user_type == user_type):
                users.append(user)
        return users
    
    # 遊戲管理
    def add_game(self, game: Game) -> bool:
        """添加遊戲"""
        if game.name in self.games:
            return False
        self.games[game.name] = game
        self.save_data()
        return True
    
    def update_game_version(self, game_name: str, version: str, description: str = "") -> bool:
        """更新遊戲版本"""
        if game_name in self.games:
            self.games[game_name].add_version(version, description)
            self.save_data()
            return True
        return False
    
    def remove_game(self, game_name: str, developer: str) -> bool:
        """移除遊戲（下架）"""
        if game_name in self.games and self.games[game_name].developer == developer:
            self.games[game_name].is_active = False
            self.save_data()
            return True
        return False
    
    def get_active_games(self) -> List[Game]:
        """獲取活躍遊戲"""
        return [game for game in self.games.values() if game.is_active]
    
    def get_developer_games(self, developer: str) -> List[Game]:
        """獲取開發者的遊戲"""
        return [game for game in self.games.values() if game.developer == developer]
    
    # 房間管理
    def create_room(self, room: Room) -> bool:
        """創建房間"""
        if room.room_id in self.rooms:
            return False
        self.rooms[room.room_id] = room
        self.save_data()
        return True
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """獲取房間"""
        return self.rooms.get(room_id)
    
    def remove_room(self, room_id: str) -> bool:
        """移除房間"""
        if room_id in self.rooms:
            del self.rooms[room_id]
            self.save_data()
            return True
        return False
    
    def get_active_rooms(self) -> List[Room]:
        """獲取活躍房間"""
        return [room for room in self.rooms.values() if room.status != "finished"]
    
    # 遊戲記錄管理
    def add_game_record(self, player: str, game_name: str, game_version: str):
        """添加遊戲記錄"""
        record = PlayerGameRecord(player, game_name, game_version)
        self.game_records.append(record)
        self.save_data()
    
    def get_player_records(self, player: str) -> List[PlayerGameRecord]:
        """獲取玩家遊戲記錄"""
        return [record for record in self.game_records if record.player == player]
    
    def add_review(self, player: str, game_name: str, rating: float, comment: str) -> bool:
        """添加遊戲評論"""
        # 檢查玩家是否玩過這個遊戲
        has_played = any(record.game_name == game_name for record in self.game_records 
                        if record.player == player)
        
        if not has_played or game_name not in self.games:
            return False
        
        self.games[game_name].add_review(player, rating, comment)
        
        # 標記該玩家已評論
        for record in self.game_records:
            if record.player == player and record.game_name == game_name:
                record.has_reviewed = True
                
        self.save_data()
        return True