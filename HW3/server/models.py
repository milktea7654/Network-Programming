from datetime import datetime
import json
from typing import Dict, List, Optional

class User:
    def __init__(self, username: str, password: str, user_type: str):
        self.username = username
        self.password = password
        self.user_type = user_type
        self.created_at = datetime.now()
        self.last_login = None
        self.is_online = False
        
    def to_dict(self):
        return {
            'username': self.username,
            'password': self.password,
            'user_type': self.user_type,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_online': self.is_online
        }
    
    @classmethod
    def from_dict(cls, data):
        user = cls(data['username'], data['password'], data['user_type'])
        user.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('last_login'):
            user.last_login = datetime.fromisoformat(data['last_login'])
        user.is_online = data.get('is_online', False)
        return user

class Game:
    def __init__(self, name: str, developer: str, description: str = "", 
                 game_type: str = "cli", max_players: int = 2):
        self.name = name
        self.developer = developer
        self.description = description
        self.game_type = game_type
        self.max_players = max_players
        self.current_version = "1.0.0"
        self.versions = {"1.0.0": {"uploaded_at": datetime.now(), "description": "Initial version"}}
        self.created_at = datetime.now()
        self.is_active = True
        self.total_rating = 0.0
        self.rating_count = 0
        self.reviews = []
        
    def add_version(self, version: str, description: str = ""):
        self.versions[version] = {
            "uploaded_at": datetime.now(),
            "description": description
        }
        self.current_version = version
        
    def get_average_rating(self):
        return self.total_rating / self.rating_count if self.rating_count > 0 else 0.0
        
    def add_review(self, player: str, rating: float, comment: str):
        review = {
            'player': player,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now().isoformat()
        }
        self.reviews.append(review)
        self.total_rating += rating
        self.rating_count += 1
        
    def to_dict(self):
        return {
            'name': self.name,
            'developer': self.developer,
            'description': self.description,
            'game_type': self.game_type,
            'max_players': self.max_players,
            'current_version': self.current_version,
            'versions': {v: {'uploaded_at': data['uploaded_at'].isoformat(), 
                           'description': data['description']} 
                        for v, data in self.versions.items()},
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'total_rating': self.total_rating,
            'rating_count': self.rating_count,
            'reviews': self.reviews
        }
    
    @classmethod
    def from_dict(cls, data):
        game = cls(data['name'], data['developer'], data['description'], 
                  data['game_type'], data['max_players'])
        game.current_version = data['current_version']
        game.versions = {v: {'uploaded_at': datetime.fromisoformat(vdata['uploaded_at']),
                           'description': vdata['description']} 
                        for v, vdata in data['versions'].items()}
        game.created_at = datetime.fromisoformat(data['created_at'])
        game.is_active = data['is_active']
        game.total_rating = data['total_rating']
        game.rating_count = data['rating_count']
        game.reviews = data['reviews']
        return game

class Room:
    def __init__(self, room_id: str, host: str, game_name: str, game_version: str, max_players: int):
        self.room_id = room_id
        self.host = host
        self.game_name = game_name
        self.game_version = game_version
        self.max_players = max_players
        self.players = [host]
        self.created_at = datetime.now()
        self.status = "waiting"
        self.game_server_port = None
        
    def add_player(self, player: str) -> bool:
        if len(self.players) < self.max_players and player not in self.players:
            self.players.append(player)
            return True
        return False
        
    def remove_player(self, player: str) -> bool:
        if player in self.players:
            self.players.remove(player)
            return True
        return False
        
    def is_full(self) -> bool:
        return len(self.players) >= self.max_players
        
    def to_dict(self):
        return {
            'room_id': self.room_id,
            'host': self.host,
            'game_name': self.game_name,
            'game_version': self.game_version,
            'max_players': self.max_players,
            'players': self.players,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'game_server_port': self.game_server_port
        }
    
    @classmethod
    def from_dict(cls, data):
        room = cls(data['room_id'], data['host'], data['game_name'], 
                  data['game_version'], data['max_players'])
        room.players = data['players']
        room.created_at = datetime.fromisoformat(data['created_at'])
        room.status = data['status']
        room.game_server_port = data.get('game_server_port')
        return room

class PlayerGameRecord:
    def __init__(self, player: str, game_name: str, game_version: str):
        self.player = player
        self.game_name = game_name
        self.game_version = game_version
        self.played_at = datetime.now()
        self.has_reviewed = False
        
    def to_dict(self):
        return {
            'player': self.player,
            'game_name': self.game_name,
            'game_version': self.game_version,
            'played_at': self.played_at.isoformat(),
            'has_reviewed': self.has_reviewed
        }
    
    @classmethod
    def from_dict(cls, data):
        record = cls(data['player'], data['game_name'], data['game_version'])
        record.played_at = datetime.fromisoformat(data['played_at'])
        record.has_reviewed = data['has_reviewed']
        return record