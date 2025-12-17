# HW2 API Documentation

## Architecture Overview

```
Client (lobby_client.py) <-> Lobby Server (port 10002) <-> Database Server (port 10001)
                                    |
                                    v
Client (game_client.py) <-> Game Server (ports 10100-10200)
```

## Protocol

**Length-Prefixed Framing Protocol**
- 4-byte header: message length (uint32, network byte order)
- Body: JSON encoded in UTF-8
- Max message size: 64 KiB (65536 bytes)

---

## Database Server API (port 10001)

### Request Format
```json
{
  "collection": "User|Room|GameLog",
  "action": "create|read|update|delete|query",
  "data": { ... }
}
```

### Response Format
```json
{
  "success": true|false,
  "data": { ... },
  "error": "error message"
}
```

### 1. User Collection

#### Create User
**Request:**
```json
{
  "collection": "User",
  "action": "create",
  "data": {
    "name": "player1",
    "email": "player1@test.com",
    "password": "123456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "userId": 1
}
```

**Logic:**
1. Hash password with SHA256
2. Insert into User table with createdAt timestamp
3. Return userId on success

#### Read User
**Request:**
```json
{
  "collection": "User",
  "action": "read",
  "data": {
    "id": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "player1",
    "email": "player1@test.com",
    "passwordHash": "...",
    "createdAt": "2025-11-13T12:00:00",
    "lastLoginAt": "2025-11-13T12:30:00"
  }
}
```

#### Query User
**Request:**
```json
{
  "collection": "User",
  "action": "query",
  "data": {
    "name": "player1"
  }
}
```
or
```json
{
  "collection": "User",
  "action": "query",
  "data": {
    "email": "player1@test.com"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "player1",
      "email": "player1@test.com",
      "passwordHash": "...",
      "createdAt": "...",
      "lastLoginAt": "..."
    }
  ]
}
```

#### Update User
**Request:**
```json
{
  "collection": "User",
  "action": "update",
  "data": {
    "id": 1,
    "updates": {
      "lastLoginAt": "2025-11-13T13:00:00"
    }
  }
}
```

**Response:**
```json
{
  "success": true
}
```

### 2. Room Collection

#### Create Room
**Request:**
```json
{
  "collection": "Room",
  "action": "create",
  "data": {
    "name": "TestRoom",
    "hostUserId": 1,
    "visibility": "public",
    "inviteList": []
  }
}
```

**Response:**
```json
{
  "success": true,
  "roomId": 1
}
```

**Logic:**
1. Insert room with status='idle'
2. Serialize inviteList as JSON
3. Set createdAt timestamp

#### Read Room
**Request:**
```json
{
  "collection": "Room",
  "action": "read",
  "data": {
    "id": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "TestRoom",
    "hostUserId": 1,
    "visibility": "public",
    "inviteList": [],
    "status": "idle",
    "createdAt": "2025-11-13T12:00:00"
  }
}
```

#### Query Room
**Request (by status):**
```json
{
  "collection": "Room",
  "action": "query",
  "data": {
    "status": "idle"
  }
}
```

**Request (by visibility):**
```json
{
  "collection": "Room",
  "action": "query",
  "data": {
    "visibility": "public"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "TestRoom",
      "hostUserId": 1,
      "visibility": "public",
      "inviteList": [],
      "status": "idle",
      "createdAt": "..."
    }
  ]
}
```

#### Update Room
**Request:**
```json
{
  "collection": "Room",
  "action": "update",
  "data": {
    "id": 1,
    "updates": {
      "status": "playing"
    }
  }
}
```

**Logic:**
- inviteList will be auto-serialized to JSON if present
- Other fields updated directly

#### Delete Room
**Request:**
```json
{
  "collection": "Room",
  "action": "delete",
  "data": {
    "id": 1
  }
}
```

### 3. GameLog Collection

#### Create GameLog
**Request:**
```json
{
  "collection": "GameLog",
  "action": "create",
  "data": {
    "matchId": "match_123",
    "roomId": 1,
    "users": [1, 2],
    "startAt": "2025-11-13T12:00:00",
    "endAt": "2025-11-13T12:10:00",
    "results": [
      {"userId": 1, "score": 1000, "rank": 1},
      {"userId": 2, "score": 800, "rank": 2}
    ]
  }
}
```

**Logic:**
1. Serialize users array to JSON
2. Serialize results array to JSON
3. Insert into GameLog table

#### Query GameLog
**Request:**
```json
{
  "collection": "GameLog",
  "action": "query",
  "data": {
    "roomId": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "matchId": "match_123",
      "roomId": 1,
      "users": [1, 2],
      "startAt": "...",
      "endAt": "...",
      "results": [...]
    }
  ]
}
```

---

## Lobby Server API (port 10002)

### Request Format
```json
{
  "action": "register|login|logout|create_room|list_rooms|join_room|leave_room|start_game|list_online_users|get_stats|spectate",
  "data": { ... }
}
```

### 1. Register
**Request:**
```json
{
  "action": "register",
  "data": {
    "name": "player1",
    "email": "player1@test.com",
    "password": "123456"
  }
}
```

**Response:**
```json
{
  "success": true
}
```

**Logic:**
1. Forward to DB server (User.create)
2. Return result

### 2. Login
**Request:**
```json
{
  "action": "login",
  "data": {
    "name": "player1",
    "password": "123456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "userId": 1,
  "name": "player1"
}
```

**Logic:**
1. Query user by name from DB
2. Verify password hash (SHA256)
3. **Check if user already logged in** (if yes, return error: "User already logged in")
4. Update lastLoginAt in DB
5. Add to online_users dict
6. Add to socket_to_user mapping
7. Initialize invitations list

### 3. Logout
**Request:**
```json
{
  "action": "logout"
}
```

**Response:**
```json
{
  "success": true
}
```

**Logic:**
1. Remove from current room if any
2. Remove from online_users
3. Remove from socket_to_user
4. Clear invitations

### 4. Create Room
**Request:**
```json
{
  "action": "create_room",
  "data": {
    "name": "TestRoom",
    "visibility": "public",
    "inviteList": []
  }
}
```

**Response:**
```json
{
  "success": true,
  "roomId": 1
}
```

**Logic:**
1. Create room in DB with hostUserId
2. Add room to local rooms dict with members=[userId]
3. Update user's room_id

### 5. List Rooms
**Request:**
```json
{
  "action": "list_rooms"
}
```

**Response:**
```json
{
  "success": true,
  "rooms": [
    {
      "id": 1,
      "name": "TestRoom",
      "visibility": "public",
      "status": "idle",
      "members": ["player1"],
      "memberCount": 1
    }
  ]
}
```

**Logic:**
1. Query all rooms from DB
2. Filter: public rooms OR rooms where user is in inviteList
3. Enhance with current members info from memory

### 6. Join Room
**Request:**
```json
{
  "action": "join_room",
  "data": {
    "roomId": 1
  }
}
```

**Response:**
```json
{
  "success": true
}
```

**Logic:**
1. Read room from DB
2. Check visibility (public OR user in inviteList)
3. Check status (must be 'idle' or 'waiting')
4. Add user to room members
5. Update user's room_id
6. Broadcast room update to all members

### 7. Leave Room
**Request:**
```json
{
  "action": "leave_room"
}
```

**Response:**
```json
{
  "success": true
}
```

**Logic:**
1. Remove user from room members
2. Clear user's room_id
3. If user was host: delete room from DB
4. Else: broadcast update to remaining members

### 8. Start Game
**Request:**
```json
{
  "action": "start_game"
}
```

**Response:**
```json
{
  "success": true,
  "gamePort": 10100,
  "players": ["player1", "player2"]
}
```

**Logic:**
1. Check user is room host
2. Check exactly 2 members in room
3. Allocate game server port (10100-10200)
4. Start game server thread
5. Update room status to 'playing' in DB
6. Create GameLog entry with startAt
7. Broadcast game start to all members

### 9. List Online Users
**Request:**
```json
{
  "action": "list_online_users"
}
```

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "userId": 1,
      "name": "player1",
      "inRoom": true
    }
  ]
}
```

### 10. Get Stats
**Request:**
```json
{
  "action": "get_stats"
}
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "totalGames": 10,
    "wins": 6,
    "losses": 4,
    "averageScore": 1500
  }
}
```

**Logic:**
1. Query all GameLogs where user participated
2. Calculate statistics from results

### 11. Spectate
**Request:**
```json
{
  "action": "spectate",
  "data": {
    "roomId": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "gamePort": 10100
}
```

**Logic:**
1. Read room from DB
2. Check status is 'playing'
3. Return game server port

---

## Game Server API (ports 10100-10200)

### Message Types

#### 1. HELLO (Client -> Server)
**Sent when:** Client connects

**Format:**
```json
{
  "type": "HELLO",
  "userId": 1,
  "username": "player1",
  "spectate": false
}
```

**Logic:**
1. If spectate=false: add to players dict, initialize TetrisGame
2. If spectate=true: add to spectators set
3. If 2 players connected: start game loop

#### 2. INPUT (Client -> Server)
**Sent when:** Player performs action

**Format:**
```json
{
  "type": "INPUT",
  "userId": 1,
  "action": "left|right|rotate_cw|rotate_ccw|soft_drop|hard_drop|hold"
}
```

**Logic:**
1. Validate player exists and game not over
2. Apply action to player's TetrisGame
3. Next broadcast will include updated state

#### 3. SNAPSHOT (Server -> Client)
**Sent when:** Game state updates (60 FPS)

**Format:**
```json
{
  "type": "SNAPSHOT",
  "userId": 1,
  "username": "player1",
  "board": "0000000000|0000000000|...",
  "active": {
    "shape": "I",
    "rotation": 0,
    "x": 3,
    "y": 0
  },
  "next": ["O", "T", "S"],
  "hold": "Z",
  "score": 1000,
  "lines": 10,
  "level": 2,
  "gameOver": false
}
```

**Logic:**
1. Encode board as RLE (run-length encoding with | separator)
2. Include current piece position
3. Include next 3 pieces
4. Include hold piece
5. Broadcast to all players and spectators

#### 4. GAME_OVER (Server -> Client)
**Sent when:** Game ends

**Format:**
```json
{
  "type": "GAME_OVER",
  "winner": 1,
  "results": [
    {"userId": 1, "username": "player1", "score": 2000, "lines": 25},
    {"userId": 2, "username": "player2", "score": 1500, "lines": 18}
  ]
}
```

**Logic:**
1. Determine winner (last surviving player OR higher score)
2. Stop game loop
3. Update GameLog in DB with endAt and results
4. Update room status to 'idle'
5. Broadcast to all clients

#### 5. GAME_END_INSUFFICIENT_PLAYERS (Server -> Client)
**Sent when:** Player count drops below 2

**Format:**
```json
{
  "type": "GAME_END_INSUFFICIENT_PLAYERS"
}
```

**Logic:**
1. Stop game loop
2. Update room status to 'idle'
3. Broadcast to remaining clients
4. Close server

---

## Game Loop Logic

**Frequency:** 60 FPS (0.0167s per frame)

**Each frame:**
1. For each player:
   - Apply gravity (piece moves down based on level)
   - Check collisions
   - If piece locked: check line clears, spawn new piece
   - If can't spawn: game over for that player
2. Check win condition (only 1 player alive)
3. Check player count (if < 2: end game)
4. Broadcast SNAPSHOT to all clients

**Line Clear:**
- 1 line: 100 * level points
- 2 lines: 300 * level points
- 3 lines: 500 * level points
- 4 lines (Tetris): 800 * level points

**Level Up:**
- Every 10 lines cleared
- Increases gravity speed

---

## Client Auto-Launch Logic

**In lobby_client.py:**

**Background thread** monitors room status every 0.5s:
```python
while True:
    if user_id and current_room_id:
        room_info = get room info
        if room.status == 'playing' and not game_launched:
            launch game_client.py subprocess
            game_launched = True
        elif room.status != 'playing' and game_launched:
            game_launched = False
    sleep(0.5)
```

**Launch command:**
```bash
python3 game_client.py <host> <port> <user_id> <room_id> <username>
```

**Purpose:**
- Auto-launch game window when host starts game
- Prevent duplicate launches with game_launched flag
- Reset flag when game ends to allow restart

---

## Security Features

### 1. Login Mutual Exclusion
- Before login: check if userId in online_users
- If already online: return error "User already logged in"
- Prevents simultaneous logins from same account

### 2. Password Hashing
- SHA256 hash stored in database
- Never transmit plain password to DB

### 3. Room Access Control
- Public rooms: anyone can join
- Private rooms: only users in inviteList can join
- Spectators: can only join rooms with status='playing'

### 4. Game State Authority
- Server-authoritative: clients send inputs, server computes state
- Prevents cheating through client modification
- Clients only render received snapshots

---

## Data Flow Examples

### Example 1: Complete Game Session

1. **Player1 logs in:**
   ```
   Client -> Lobby: {action: "login", data: {name: "player1", password: "123"}}
   Lobby -> DB: {collection: "User", action: "query", data: {name: "player1"}}
   DB -> Lobby: {success: true, data: [{id: 1, ...}]}
   Lobby -> Client: {success: true, userId: 1}
   ```

2. **Player1 creates room:**
   ```
   Client -> Lobby: {action: "create_room", data: {name: "Room1", visibility: "public"}}
   Lobby -> DB: {collection: "Room", action: "create", data: {...}}
   DB -> Lobby: {success: true, roomId: 1}
   Lobby -> Client: {success: true, roomId: 1}
   ```

3. **Player2 joins room:**
   ```
   Client -> Lobby: {action: "join_room", data: {roomId: 1}}
   Lobby -> DB: {collection: "Room", action: "read", data: {id: 1}}
   Lobby -> Client: {success: true}
   Lobby -> All room members: {type: "ROOM_UPDATE", ...}
   ```

4. **Player1 starts game:**
   ```
   Client -> Lobby: {action: "start_game"}
   Lobby -> DB: {collection: "Room", action: "update", data: {id: 1, updates: {status: "playing"}}}
   Lobby -> DB: {collection: "GameLog", action: "create", data: {...}}
   Lobby starts Game Server on port 10100
   Lobby -> All room members: {type: "GAME_START", gamePort: 10100}
   ```

5. **Game clients connect:**
   ```
   Game Client1 -> Game Server: {type: "HELLO", userId: 1, spectate: false}
   Game Client2 -> Game Server: {type: "HELLO", userId: 2, spectate: false}
   Game Server starts game loop (60 FPS)
   ```

6. **Gameplay:**
   ```
   Game Client -> Game Server: {type: "INPUT", action: "rotate_cw"}
   Game Server (every frame) -> All clients: {type: "SNAPSHOT", ...}
   ```

7. **Game ends:**
   ```
   Game Server -> All clients: {type: "GAME_OVER", winner: 1, results: [...]}
   Game Server -> DB: {collection: "GameLog", action: "update", data: {endAt: ..., results: [...]}}
   Game Server -> Lobby: Update room status to 'idle'
   ```

### Example 2: Spectator Joins

1. **Spectator checks room:**
   ```
   Client -> Lobby: {action: "spectate", data: {roomId: 1}}
   Lobby -> DB: {collection: "Room", action: "read", data: {id: 1}}
   Lobby -> Client: {success: true, gamePort: 10100}
   ```

2. **Spectator connects:**
   ```
   Spectator Client -> Game Server: {type: "HELLO", userId: 3, spectate: true}
   Game Server -> Spectator: {type: "SNAPSHOT", ...} (every frame)
   ```

---

## Error Handling

### Connection Errors
- Client disconnect: remove from online_users, remove from room
- Server crash: clients detect connection loss, exit gracefully
- Partial send/receive: protocol._send_all/_recv_all handles

### Game Errors
- Player disconnect during game: other player wins automatically
- Both players disconnect: game ends, no winner
- Invalid input: ignored, game continues

### Database Errors
- Connection timeout: retry mechanism (not implemented)
- Constraint violation: return error to client
- Lock timeout: SQLite handles automatically

---

## Port Allocation

- **10001**: Database Server (fixed)
- **10002**: Lobby Server (fixed)
- **10100-10200**: Game Servers (dynamic allocation, max 100 concurrent games)

Game server port selection:
```python
for port in range(10100, 10201):
    if port not in active_game_ports:
        return port
```
