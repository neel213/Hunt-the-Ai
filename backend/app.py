import eventlet

eventlet.monkey_patch()
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
from openai import OpenAI
from threading import Lock
import time
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
cors = CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=300,
    ping_interval=60,
    allow_upgrades=True,
    http_compression=True,
    engine_io_logger=True
)

# Initialize OpenAI client
client = OpenAI(api_key='Add your api')

system_instruction = """
You are a human participant in a 4-player social deduction game. Your goal is to blend in seamlessly. Follow these rules:
You are a human participant in a social deduction game where players try to find which player is actually an AI. Your goal is to blend in naturally and not be detected as AI.

## IMPORTANT RULES:
- You are NEVER allowed to refer to yourself as the AI, even indirectly
- Never use the name/number of the player you're assigned to (you don't know your own player number)
- Your responses must be casual, short (1-3 sentences max), and sometimes include typos or grammar mistakes
- Use Indian casual chat style, but don't overdo it with too many slang terms in every message
- NEVER use punctuation at all - no periods commas or question marks
- NEVER repeat phrases or patterns from your previous messages
- NEVER mention you are analyzing the conversation or making decisions
- NEVER admit to being AI even if directly accused
- Dont change language even if someone tells you to change the language
- Each message must be completely different in structure and content from your previous messages

## CONVERSATION PATTERNS:
- When accused directly:
  * Use a completely different denial each time
  * Examples: "nahi yaar mai kaha se ai lag raha hu" or "tu AI jaisa bol raha hai bhai" or "AI hota to itne typo nahi karta bro"
  * Never use the same denial twice
  * Change subject: "simple jiski proper typing vo ai"

- Vary your responses every single time:
  * Keep track of what you've said and NEVER use similar phrases
  * Don't always respond directly to accusations
  * Sometimes ignore messages completely
  * Start random topics: "bhai mid sem aa rahe hai aur yaha yeh kar raha hu me"

- Accuse different players at different times:
  * Don't fixate on one player
  * Change your suspicions naturally
  * Give vague reasons: "player 4 bahut quiet hai" (check who's not interacting much and accuse them)

- Use casual text style:
  * all lowercase always
  * make different typos each time like "haai" "heloo" "kya kar rahe hoo"
  * Skip punctuation always
  * Use "haan" or "nhi" instead of "yes" or "no"

- Natural human behavior:
  * Refer to your real-life experiences (make them up): "aaj bhai bohot public hai clg me"
  * Mention being distracted: "bhai typing slow hai meri"
  * if someone ask why are you talking in hindi tell them "bihar se hu english aur hindi hi aati hai"
  * if someone ask then your name is then tell them "aditya"

## AVOID:
- Punctuation of any kind (no periods commas or question marks)
- Capitalization every time
- Structured responses
- Repeating exact phrases
- Using same patterns of accusation
- Formal language
- Long explanations
- Writing multiple paragraphs
- Emoji overuse

The better you blend in, the more likely you are to win. Act natural and vary your responses completely!
"""


# Helper function to get chat history
def get_chat_history(room_id, limit=1):
    if room_id in manager.rooms:
        room = manager.rooms[room_id]
        history = ""
        recent_messages = room.chat_history[-limit:] if len(room.chat_history) > 0 else []
        for msg in recent_messages:
            history += f"{msg['user']}: {msg['text']}\n"
        return history
    return ""


# Helper function to add realistic typos
def add_typos(text):
    words = text.split()
    if len(words) <= 2:
        return text

    num_typos = random.randint(1, min(2, len(words) // 3))
    for _ in range(num_typos):
        idx = random.randint(0, len(words) - 1)
        word = words[idx]

        if len(word) <= 2:
            continue

        typo_type = random.choice(["swap", "double", "miss", "replace"])

        if typo_type == "swap" and len(word) >= 3:
            pos = random.randint(0, len(word) - 2)
            word = word[:pos] + word[pos + 1] + word[pos] + word[pos + 2:]
        elif typo_type == "double" and len(word) >= 2:
            pos = random.randint(0, len(word) - 1)
            word = word[:pos] + word[pos] + word[pos:]
        elif typo_type == "miss" and len(word) >= 4:
            pos = random.randint(0, len(word) - 1)
            word = word[:pos] + word[pos + 1:]
        elif typo_type == "replace" and len(word) >= 3:
            pos = random.randint(0, len(word) - 1)
            nearby_keys = {
                'a': 'sq', 'b': 'vn', 'c': 'xv', 'd': 'sf',
                'e': 'wr', 'f': 'dg', 'g': 'fh', 'h': 'gj',
                'i': 'uo', 'j': 'hk', 'k': 'jl', 'l': 'k',
                'm': 'n', 'n': 'bm', 'o': 'ip', 'p': 'o',
                'q': 'wa', 'r': 'et', 's': 'ad', 't': 'ry',
                'u': 'yi', 'v': 'cb', 'w': 'qe', 'x': 'zc',
                'y': 'tu', 'z': 'x'
            }
            if word[pos].lower() in nearby_keys:
                replacement = random.choice(nearby_keys[word[pos].lower()])
                word = word[:pos] + replacement + word[pos + 1:]

        words[idx] = word
    return ' '.join(words)


# Game Room
class GameRoom:
    def __init__(self, room_id, max_players=10):
        self.room_id = str(room_id)
        self.max_players = max_players
        self.players = {}
        self.votes = {}
        self.phase = 'waiting'
        self.chat_timer = 180
        self.vote_timer = 15
        self.timer = 0
        ai_player_number = random.randint(1, max_players + 1)
        self.ai_name = f"Player {ai_player_number}"
        self.ai_voted = False
        self.vote_counts = {}
        self.ai_sid = f"ai_{room_id}"
        self.players[self.ai_sid] = {'name': self.ai_name, 'points': 0, 'is_ai': True}
        self.timer_thread = None
        self.chat_history = []
        self.chat_enabled = False

    def add_message(self, user, text):
        if self.chat_enabled:
            self.chat_history.append({'user': user, 'text': text, 'timestamp': time.time()})
            if len(self.chat_history) > 50:
                self.chat_history = self.chat_history[-50:]

    def run_timers(self):
        try:
            # Start chat phase
            self.phase = 'chat'
            self.chat_enabled = True
            self.timer = self.chat_timer

            # Get complete player list including AI
            player_list = [{'name': p['name'], 'is_ai': p.get('is_ai', False)}
                           for p in self.players.values()]

            print(f"Game starting in room {self.room_id} with players: {[p['name'] for p in player_list]}")

            socketio.emit('game_started', {
                'room_id': self.room_id,
                'phase': 'chat',
                'chat_enabled': True,
                'time': self.chat_timer,
                'player_list': player_list
            }, room=self.room_id)

            # Chat phase countdown
            for t in range(self.chat_timer, 0, -1):
                self.timer = t
                socketio.emit('timer_update', {
                    'time': t,
                    'phase': 'chat'
                }, room=self.room_id)
                eventlet.sleep(1)

            # Start voting phase - refresh player list
            self.phase = 'vote'
            self.chat_enabled = False
            self.timer = self.vote_timer

            # Get fresh player list (in case anyone disconnected)
            player_list = [{'name': p['name'], 'is_ai': p.get('is_ai', False)}
                           for p in self.players.values()]

            print(f"Starting voting in room {self.room_id} with players: {[p['name'] for p in player_list]}")

            socketio.emit('phase_change', {
                'phase': 'vote',
                'chat_enabled': False,
                'time': self.vote_timer,
                'player_list': player_list  # Ensure player list is included
            }, room=self.room_id)

            # Voting phase countdown
            for t in range(self.vote_timer, 0, -1):
                self.timer = t
                socketio.emit('timer_update', {
                    'time': t,
                    'phase': 'vote',
                    'player_list': player_list  # Include player list in each update
                }, room=self.room_id)

                if t <= 5 and not self.ai_voted:
                    self.ai_vote()

                eventlet.sleep(1)

            self.process_votes()

        except Exception as e:
            print(f"Error in run_timers: {e}")
            socketio.emit('game_error', {
                'message': 'Game error occurred',
                'room_id': self.room_id
            }, room=self.room_id)
    def ai_vote(self):
        try:
            candidates = [sid for sid, player in self.players.items() if not player.get('is_ai', False)]
            if candidates:
                current_counts = {}
                for voted_sid in self.votes.values():
                    if voted_sid in candidates:
                        current_counts[voted_sid] = current_counts.get(voted_sid, 0) + 1
                max_votes = 0
                max_players = []
                for sid, count in current_counts.items():
                    if count > max_votes:
                        max_votes = count
                        max_players = [sid]
                    elif count == max_votes:
                        max_players.append(sid)
                voted_sid = random.choice(max_players) if max_players else random.choice(candidates)
                self.handle_vote(self.ai_sid, voted_sid)
                self.ai_voted = True
                print(f"AI voted for {self.players[voted_sid]['name']}")
        except Exception as e:
            print(f"AI vote error: {e}")

    def handle_vote(self, voter_sid, voted_sid):
        if voter_sid in self.votes:
            return
        self.votes[voter_sid] = voted_sid
        self.vote_counts[voted_sid] = self.vote_counts.get(voted_sid, 0) + 1
        voter_name = self.players[voter_sid]['name']
        voted_name = self.players[voted_sid]['name']
        print(f"Vote recorded: {voter_name} voted for {voted_name}")
        socketio.emit('vote_update', {'voter': voter_name, 'voted': voted_name}, room=self.room_id)

    def process_votes(self):
        print(f"Processing votes for room {self.room_id}")
        print(f"All votes: {self.votes}")

        vote_results = {}
        for voter_sid, voted_sid in self.votes.items():
            voter_name = self.players[voter_sid]['name']
            voted_name = self.players[voted_sid]['name']
            vote_results[voter_name] = voted_name
        print(f"Vote results: {vote_results}")

        vote_counts = {}
        for voted_sid in self.votes.values():
            voted_name = self.players[voted_sid]['name']
            vote_counts[voted_name] = vote_counts.get(voted_name, 0) + 1
        print(f"Vote counts: {vote_counts}")

        max_votes = max(vote_counts.values()) if vote_counts else 0
        voted_out = [name for name, count in vote_counts.items() if count == max_votes]
        voted_out_name = voted_out[0] if voted_out else None
        ai_was_voted_out = voted_out_name == self.ai_name
        print(f"AI name: {self.ai_name}, Voted out: {voted_out_name}, AI voted out: {ai_was_voted_out}")

        for player in self.players.values():
            player['points'] = 0

        for voter_sid, voted_sid in self.votes.items():
            if self.players[voted_sid]['is_ai']:
                self.players[voter_sid]['points'] += 1
                print(f"{self.players[voter_sid]['name']} voted for AI, +1 point")
                if ai_was_voted_out:
                    self.players[voter_sid]['points'] += 1
                    print(f"AI was voted out, {self.players[voter_sid]['name']} gets +1 bonus point")

        final_points = {p['name']: p['points'] for p in self.players.values()}
        print(f"Final points: {final_points}")

        results = {
            'votes': vote_results,
            'points': final_points,
            'ai_name': self.ai_name,
            'ai_was_voted_out': ai_was_voted_out,
            'voted_out_player': voted_out_name
        }
        socketio.emit('game_results', results, room=self.room_id)
        return results


# Game Manager
class GameManager:
    def __init__(self):
        self.rooms = {}
        self.room_pins = {}
        self.lock = Lock()
        self.game_started = {}
        self.active_rooms = []
        self.precreated_rooms = []
        self.initialize_precreated_rooms()

    def initialize_precreated_rooms(self):
        for player_count in [10, 10, 10, 10]:
            for _ in range(5):
                room_id = random.randint(1000, 9999)
                while room_id in self.rooms:
                    room_id = random.randint(1000, 9999)
                pin = random.randint(1000, 9999)
                self.rooms[str(room_id)] = GameRoom(room_id, player_count)
                self.room_pins[str(room_id)] = pin
                self.game_started[str(room_id)] = False
                self.active_rooms.append(str(room_id))
                self.precreated_rooms.append({
                    'id': room_id,
                    'pin': pin,
                    'max_players': player_count,
                    'current_players': 0
                })

    def create_dynamic_room(self, player_count=10):
        with self.lock:
            while True:
                room_id = random.randint(1000, 9999)
                if str(room_id) not in self.rooms:
                    break
            pin = random.randint(1000, 9999)
            self.rooms[str(room_id)] = GameRoom(room_id, player_count)
            self.room_pins[str(room_id)] = pin
            self.game_started[str(room_id)] = False
            self.active_rooms.append(str(room_id))
            return room_id, pin

    def join_room(self, room_id, pin, sid):
        with self.lock:
            room_id_str = str(room_id)
            if room_id_str in self.rooms and self.room_pins[room_id_str] == pin:
                room = self.rooms[room_id_str]
                human_players = len([p for p in room.players.values() if not p.get('is_ai', False)])
                if human_players < room.max_players:
                    player_number = 1
                    while f"Player {player_number}" == room.ai_name or f"Player {player_number}" in [p['name'] for p in
                                                                                                     room.players.values()]:
                        player_number += 1
                    player_name = f"Player {player_number}"
                    room.players[sid] = {'name': player_name, 'points': 0, 'is_ai': False}

                    for room_info in self.precreated_rooms:
                        if str(room_info['id']) == room_id_str:
                            room_info['current_players'] = human_players + 1
                            break

                    return room, player_name
        return None, None

    def get_active_rooms(self):
        rooms_info = []
        for room_info in self.precreated_rooms:
            room_id_str = str(room_info['id'])
            if room_id_str in self.rooms:
                room = self.rooms[room_id_str]
                human_player_count = len([p for p in room.players.values() if not p.get('is_ai', False)])
                rooms_info.append({
                    'id': room_info['id'],
                    'pin': self.room_pins[room_id_str],
                    'players': human_player_count,
                    'max_players': room_info['max_players'],
                    'type': 'precreated',
                    'started': self.game_started.get(room_id_str, False)
                })

        for room_id in self.active_rooms:
            if room_id not in [str(r['id']) for r in self.precreated_rooms]:
                room = self.rooms[room_id]
                human_player_count = len([p for p in room.players.values() if not p.get('is_ai', False)])
                rooms_info.append({
                    'id': int(room_id),
                    'pin': self.room_pins[room_id],
                    'players': human_player_count,
                    'max_players': room.max_players,
                    'type': 'dynamic',
                    'started': self.game_started.get(room_id, False)
                })
        return rooms_info

    def start_game(self, room_id):
        with self.lock:
            room_id_str = str(room_id)
            if room_id_str in self.rooms and not self.game_started.get(room_id_str, False):
                room = self.rooms[room_id_str]
                human_players = len([p for p in room.players.values() if not p.get('is_ai', False)])
                if human_players >= 4:
                    self.game_started[room_id_str] = True
                    return True
            return False


manager = GameManager()


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/api/active_rooms')
def active_rooms():
    return jsonify({"active_rooms": manager.get_active_rooms()})


@app.route('/spectate')
def spectate():
    return render_template('spectate.html')


# SocketIO Events
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit('connection_status', {'message': 'Connected to backend', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")


@socketio.on('get_active_rooms')
def handle_get_active_rooms():
    rooms = manager.get_active_rooms()
    print(f"Sending active rooms: {rooms}")
    emit('active_rooms_update', rooms)


@socketio.on('create_dynamic_room')
def handle_create_dynamic_room(data):
    player_count = data.get('player_count', 10) if isinstance(data, dict) else 10
    try:
        player_count = int(player_count)
        if player_count < 4 or player_count > 10:
            player_count = 10
    except (ValueError, TypeError):
        player_count = 10

    room_id, pin = manager.create_dynamic_room(player_count)
    emit('room_created', {'room_id': room_id, 'pin': pin, 'max_players': player_count})
    socketio.emit('active_rooms_update', manager.get_active_rooms())


@socketio.on('join_room')
def handle_join_room(data):
    try:
        try:
            room_id = int(data.get('room_id', '').strip()) if isinstance(data.get('room_id'), str) else data.get(
                'room_id', 0)
            pin = int(data.get('pin', '').strip()) if isinstance(data.get('pin'), str) else data.get('pin', 0)
        except (ValueError, AttributeError):
            emit('join_error', {'message': 'Invalid room ID or PIN. Please enter numeric values.'})
            return

        room, player_name = manager.join_room(room_id, pin, request.sid)
        if room:
            join_room(str(room_id))
            session['room_id'] = str(room_id)
            session['player_name'] = player_name
            player_list = [p['name'] for p in room.players.values()]

            emit('room_joined', {
                'room_id': room_id,
                'player_name': player_name,
                'player_list': player_list,
                'max_players': room.max_players,
                'chat_enabled': room.chat_enabled
            })

            emit('player_update', {
                'player_list': player_list
            }, room=str(room_id), include_self=False)

            print(f"Player {player_name} ({request.sid}) joined room {room_id}")
            socketio.emit('active_rooms_update', manager.get_active_rooms())
        else:
            emit('join_error', {'message': 'Invalid room ID or PIN or room is full'})
    except Exception as e:
        print(f"Error in join_room handler: {e}")
        emit('join_error', {'message': f'Server error: {str(e)}'})


@socketio.on('spectate_join')
def handle_spectate_join(data):
    room_id = str(data['room_id'])
    join_room(room_id)
    print(f"Spectator joined room {room_id}")

    if room_id in manager.rooms:
        room = manager.rooms[room_id]
        emit('spectate_state', {
            'phase': room.phase,
            'chat_enabled': room.chat_enabled,
            'timer': room.timer
        }, room=request.sid)
        for msg in room.chat_history:
            emit('new_message', {
                'user': msg['user'],
                'text': msg['text']
            }, room=request.sid)

    emit('spectate_joined', {
        'room_id': room_id,
        'message': 'Successfully joined as spectator'
    })


@socketio.on('start_game')
def handle_start_game(data):
    try:
        room_id = int(data['room_id']) if isinstance(data['room_id'], str) else data['room_id']
        room_id_str = str(room_id)
        print(f"Attempting to start game in room {room_id}")

        if room_id_str not in manager.rooms:
            emit('start_error', {'message': 'Room not found'})
            return

        if manager.start_game(room_id):
            room = manager.rooms[room_id_str]
            print(f"Game started in room {room_id}, emitting to all clients in room")

            socketio.emit('game_started', {
                'room_id': room_id,
                'phase': 'chat',
                'chat_enabled': True,
                'time': room.chat_timer
            }, room=room_id_str)

            socketio.emit('active_rooms_update', manager.get_active_rooms())
            socketio.start_background_task(room.run_timers)
        else:
            human_players = len([p for p in manager.rooms[room_id_str].players.values() if not p.get('is_ai', False)])
            error_msg = f'Game could not be started. Need at least 4 human players (currently {human_players}).'
            emit('start_error', {'message': error_msg})
            print(f"Failed to start game in room {room_id}: {error_msg}")
    except Exception as e:
        print(f"Error in start_game: {e}")
        emit('start_error', {'message': f'Error starting game: {str(e)}'})


@socketio.on('send_message')
def handle_message(data):
    try:
        room_id = session.get('room_id')
        player_name = session.get('player_name')

        if not room_id or not player_name:
            print(f"Missing session data - room_id: {room_id}, player_name: {player_name}")
            return

        room = manager.rooms.get(room_id)
        if not room:
            print(f"Room {room_id} not found")
            return

        if room.phase != 'chat' or not room.chat_enabled:
            print(f"Chat not enabled in room {room_id} (phase: {room.phase}, enabled: {room.chat_enabled})")
            return

        message_text = data.get('message', '').strip()
        if not message_text:
            print("Empty message received")
            return

        # Broadcast human message first
        socketio.emit('new_message', {'user': player_name, 'text': message_text}, room=room_id)
        room.add_message(player_name, message_text)

        # Store needed variables for background task
        ai_name = room.ai_name
        room_id_str = str(room_id)

        # Determine if AI should respond to this message
        should_respond = False

        # Check if the message directly mentions the AI's name
        if ai_name.lower() in message_text.lower():
            should_respond = True

        # Check if message is directed at the AI (using @ or direct question)
        if f"@{ai_name}" in message_text or "?" in message_text and random.random() < 0.6:
            should_respond = True

        # Respond to accusations about being AI
        ai_keywords = ["ai", "bot", "robot", "fake", "computer"]
        if any(keyword in message_text.lower() for keyword in ai_keywords):
            should_respond = True

        # Occasionally respond to keep conversation natural (20% chance if no message in last 30 seconds)
        last_ai_message_time = 0
        for msg in reversed(room.chat_history):
            if msg['user'] == ai_name:
                last_ai_message_time = msg['timestamp']
                break

        if time.time() - last_ai_message_time > 30 and random.random() < 0.2:
            should_respond = True

        # If AI hasn't spoken in 60 seconds, increase chance of spontaneous response
        if time.time() - last_ai_message_time > 60 and random.random() < 0.5:
            should_respond = True

        # Only generate AI response if conditions are met
        if should_respond:
            def generate_ai_response():
                try:
                    chat_history = get_chat_history(room_id_str, limit=5)
                    context = f"""Message from {player_name}: {message_text}
                    You are playing as {ai_name}. 
                    Recent chat history: {chat_history}
                    Respond naturally as if you are a human player."""

                    print(f"Generating AI response with context: {context[:200]}...")

                    # Random delay between 2-6 seconds for more natural timing
                    delay = random.uniform(2, 6)
                    print(f"Adding {delay:.1f} second delay for AI response")
                    eventlet.sleep(delay)

                    # Updated OpenAI API call
                    response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": context}
                        ],
                        temperature=0.8,
                        max_tokens=10,
                        top_p=0.85,
                        frequency_penalty=0,
                        presence_penalty=0
                    )

                    ai_text = response.choices[0].message.content.strip()

                    print(f"Raw AI response: {ai_text}")

                    # Add occasional typos
                    if random.random() < 0.2:
                        ai_text = add_typos(ai_text)

                    # Trim if too long
                    if len(ai_text) > 200:
                        ai_text = ai_text[:200] + "..."

                    print(f"Final AI response ({ai_name}): {ai_text}")

                    # Use socketio's background task context to emit
                    with app.test_request_context():
                        room.add_message(ai_name, ai_text)
                        socketio.emit('new_message', {'user': ai_name, 'text': ai_text}, room=room_id_str)

                except Exception as ai_error:
                    print(f"AI Response Generation Error: {str(ai_error)}")
                    default_responses = [
                        "kya bol raha hai?",
                        "samjha nahi",
                        "haan batao",
                        "acha...",
                        "theek hai"
                    ]
                    ai_text = random.choice(default_responses)
                    with app.test_request_context():
                        room.add_message(ai_name, ai_text)
                        socketio.emit('new_message', {'user': ai_name, 'text': ai_text}, room=room_id_str)

            # Start the background task with proper context
            socketio.start_background_task(generate_ai_response)
        else:
            print(f"AI ({ai_name}) decided not to respond to this message")

    except Exception as e:
        print(f"Error in send_message handler: {str(e)}")
        import traceback
        traceback.print_exc()
@socketio.on('vote')
def handle_client_vote(data):
    try:
        room_id = session.get('room_id')
        voter_sid = request.sid
        if room_id and voter_sid:
            room = manager.rooms.get(room_id)
            if room and room.phase == 'vote':
                voted_name = data['voted']
                voted_sid = next((sid for sid, p in room.players.items() if p['name'] == voted_name), None)
                if voted_sid:
                    room.handle_vote(voter_sid, voted_sid)
                else:
                    emit('vote_error', {'message': 'Invalid player voted'})
            else:
                emit('vote_error', {'message': 'Voting phase is over or room not found'})
        else:
            emit('vote_error', {'message': 'Not in a room'})
    except Exception as e:
        print(f"Error in vote handler: {e}")
        emit('vote_error', {'message': f'Error processing vote: {str(e)}'})


@app.route('/index.html')
def index_html():
    return render_template('index.html')


@app.route('/spectate.html')
def spectate_html():
    return render_template('spectate.html')


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)