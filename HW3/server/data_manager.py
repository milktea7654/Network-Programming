#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from models import User, Game, Room, PlayerGameRecord

class DataManager:
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.users_file = os.path.join(data_dir, "users.json")
        self.games_file = os.path.join(data_dir, "games.json")
        self.rooms_file = os.path.join(data_dir, "rooms.json")
        self.records_file = os.path.join(data_dir, "game_records.json")
        
        self.users = {}
        self.games = {}
        self.rooms = {}
        self.game_records = []
        
        self.load_data()
    
    def load_data(self):
        print(f"\n正在加載數據...")
        print(f"   數據目錄: {self.data_dir}")
        print(f"   遊戲文件: {self.games_file}")
        
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    for username, data in users_data.items():
                        self.users[username] = User.from_dict(data)
                print(f"   加載 {len(self.users)} 個用戶")
            
            if os.path.exists(self.games_file):
                with open(self.games_file, 'r', encoding='utf-8') as f:
                    games_data = json.load(f)
                    for game_name, data in games_data.items():
                        self.games[game_name] = Game.from_dict(data)
                        print(f"   加載遊戲: {game_name} (is_active={self.games[game_name].is_active})")
                print(f"   加載 {len(self.games)} 個遊戲")
            else:
                print(f"   遊戲文件不存在: {self.games_file}")
            
            if os.path.exists(self.rooms_file):
                with open(self.rooms_file, 'r', encoding='utf-8') as f:
                    rooms_data = json.load(f)
                    for room_id, data in rooms_data.items():
                        self.rooms[room_id] = Room.from_dict(data)
            
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    records_data = json.load(f)
                    for data in records_data:
                        self.game_records.append(PlayerGameRecord.from_dict(data))
                        
            print(f"數據加載完成: {len(self.users)} 用戶, {len(self.games)} 遊戲, {len(self.rooms)} 房間")
            
        except Exception as e:
            print(f"加載數據時出錯: {e}")
    
    def save_data(self):
        try:
            users_data = {username: user.to_dict() for username, user in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            
            games_data = {game_name: game.to_dict() for game_name, game in self.games.items()}
            with open(self.games_file, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, ensure_ascii=False, indent=2)
            
            print(f"數據已保存 - {len(self.users)} 用戶, {len(self.games)} 遊戲, {len(self.rooms)} 房間")
            
            rooms_data = {room_id: room.to_dict() for room_id, room in self.rooms.items()}
            with open(self.rooms_file, 'w', encoding='utf-8') as f:
                json.dump(rooms_data, f, ensure_ascii=False, indent=2)
            
            records_data = [record.to_dict() for record in self.game_records]
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(records_data, f, ensure_ascii=False, indent=2)
            
            print(f"[DEBUG] 已保存 {len(self.game_records)} 條遊戲記錄到 {self.records_file}")
                
        except Exception as e:
            print(f"保存數據時出錯: {e}")
    
    def create_user(self, username: str, password: str, user_type: str) -> bool:
        if username in self.users:
            return False
        self.users[username] = User(username, password, user_type)
        self.save_data()
        return True
    
    def authenticate_user(self, username: str, password: str, user_type: str) -> Optional[User]:
        if username in self.users:
            user = self.users[username]
            if user.password == password and user.user_type == user_type:
                return user
        return None
    
    def set_user_online(self, username: str, status: bool):
        if username in self.users:
            self.users[username].is_online = status
            if status:
                self.users[username].last_login = datetime.now()
            self.save_data()
    
    def get_online_users(self, user_type: str = None) -> List[User]:
        users = []
        for user in self.users.values():
            if user.is_online and (user_type is None or user.user_type == user_type):
                users.append(user)
        return users
    
    def add_game(self, game: Game) -> bool:
        if game.name in self.games:
            return False
        self.games[game.name] = game
        self.save_data()
        return True
    
    def update_game_version(self, game_name: str, version: str, description: str = "") -> bool:
        if game_name in self.games:
            self.games[game_name].add_version(version, description)
            self.save_data()
            return True
        return False
    
    def remove_game(self, game_name: str, developer: str) -> bool:
        if game_name in self.games and self.games[game_name].developer == developer:
            print(f"DEBUG: 下架遊戲 '{game_name}'")
            print(f"   下架前 is_active: {self.games[game_name].is_active}")
            self.games[game_name].is_active = False
            print(f"   下架後 is_active: {self.games[game_name].is_active}")
            self.save_data()
            print(f"   數據已保存")
            active_games = self.get_active_games()
            print(f"   當前活躍遊戲數量: {len(active_games)}")
            print(f"   活躍遊戲列表: {[g.name for g in active_games]}")
            return True
        return False
    
    def get_active_games(self) -> List[Game]:
        return [game for game in self.games.values() if game.is_active]
    
    def get_developer_games(self, developer: str) -> List[Game]:
        return [game for game in self.games.values() if game.developer == developer]
    
    def create_room(self, room: Room) -> bool:
        if room.room_id in self.rooms:
            return False
        self.rooms[room.room_id] = room
        self.save_data()
        return True
    
    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)
    
    def remove_room(self, room_id: str) -> bool:
        if room_id in self.rooms:
            del self.rooms[room_id]
            self.save_data()
            return True
        return False
    
    def get_active_rooms(self) -> List[Room]:
        return [room for room in self.rooms.values() if room.status != "finished"]
    
    def add_game_record(self, player: str, game_name: str, game_version: str):
        record = PlayerGameRecord(player, game_name, game_version)
        self.game_records.append(record)
        print(f"[DEBUG] 添加遊戲記錄: 玩家={player}, 遊戲={game_name}, 版本={game_version}")
        print(f"[DEBUG] 當前記錄總數: {len(self.game_records)}")
        self.save_data()
    
    def get_player_records(self, player: str) -> List[PlayerGameRecord]:
        records = [record for record in self.game_records if record.player == player]
        print(f"[DEBUG] get_player_records: player={player}, 找到 {len(records)} 條記錄")
        return records
    
    def add_review(self, player: str, game_name: str, rating: float, comment: str) -> bool:
        print(f"[DEBUG] add_review 被調用: player={player}, game_name={game_name}")
        print(f"[DEBUG] 當前遊戲記錄總數: {len(self.game_records)}")
        
        player_records = [r for r in self.game_records if r.player == player]
        print(f"[DEBUG] 玩家 {player} 的記錄數: {len(player_records)}")
        for r in player_records:
            print(f"[DEBUG]   - 遊戲: {r.game_name}, 版本: {r.game_version}, 已評論: {r.has_reviewed}")
        
        has_played = any(record.game_name == game_name for record in self.game_records 
                        if record.player == player)
        
        print(f"[DEBUG] has_played={has_played}, game_name in games={game_name in self.games}")
        
        if not has_played or game_name not in self.games:
            return False
        
        self.games[game_name].add_review(player, rating, comment)
        
        for record in self.game_records:
            if record.player == player and record.game_name == game_name and not record.has_reviewed:
                record.has_reviewed = True
                break
                
        self.save_data()
        return True