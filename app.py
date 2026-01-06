# This file sets up a Flask application with SocketIO for real-time communication.
# It serves an index page and handles incoming messages from clients.
import time

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from server.game_state import PokerGame  # Class is in server/game_state.py
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Initialize game logic
game = PokerGame()

@app.route('/')
def index():
    return render_template('index.html')

TURN_SECONDS = 15

timer_lock = Lock()
turn_token = 0          # increments each time a new turn starts
timer_task = None       # background task handle
turn_expires_at = None  # epoch seconds

def start_turn_timer():
    """Start/reset the per-turn countdown and broadcast ticks."""
    global turn_token, timer_task, turn_expires_at

    with timer_lock:
        # advance token to invalidate any previous loop
        turn_token += 1
        my_token = turn_token

        # set new expiry
        if game.current_turn:
            turn_expires_at = time.time() + TURN_SECONDS
        else:
            turn_expires_at = None
            return

        # launch background loop
        def _tick():
            while True:
                with timer_lock:
                    if my_token != turn_token:
                        return  # a newer turn began
                    remaining = max(0, int(turn_expires_at - time.time()))
                    current_name = game.players.get(game.current_turn, {}).get('name')
                    socketio.emit('timer', {
                        'remaining': remaining,
                        'current_turn_name': current_name
                    })
                    if remaining == 0:
                        # timeout -> auto-fold current player
                        sid = game.current_turn
                        if sid and sid in game.players and not game.players[sid]['folded']:
                            game.process_action(sid, 'fold')
                        game.advance_turn()
                        socketio.emit('state', game.get_state())
                        # start next player's timer
                        start_turn_timer()
                        return
                socketio.sleep(1)

        # start a new background task
        socketio.start_background_task(_tick)

# Handle player joining
@socketio.on('join')
def handle_join(data):
    name = data['name']
    sid = request.sid
    added = game.add_player(sid, name)
    if not added:
        emit('error', {'chat': 'Name taken or table full'}, to=sid)
        return
    print(f"{name} joined the game.")
    socketio.emit('chat', f"🔔 {name} has joined the game.")
    broadcast_state()
    # if the first player just joined or it's their turn, (re)start timer
    start_turn_timer()

# Handle disconnection
@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    player = game.players.pop(sid, None)
    if player:
        print(f"{player['name']} disconnected.")
        socketio.emit('chat', f"❌ {player['name']} has left the game.")
        # if current turn left, advance and restart timer
        if game.current_turn == sid:
            game.advance_turn()
            broadcast_state()
            start_turn_timer()
        else:
            broadcast_state()

# Handle chat messages
@socketio.on('chat')
def handle_chat(data):
    user = data.get('user')
    msg = data.get('msg')
    full_msg = f"{user}: {msg}"
    print(f"chat: {full_msg}")
    emit('chat', full_msg, broadcast=True)

# Broadcast game state to all clients
def broadcast_state():
    emit('state', game.get_state(), broadcast=True)

# Handle player actions like betting or folding
@socketio.on('action')
def handle_action(data):
    sid = request.sid
    if sid != game.current_turn:
        emit('error', {'message': 'Not your turn'}, to=sid)
        return

    action = data['type']
    game.process_action(sid, action)
    game.advance_turn()
    broadcast_state()
    start_turn_timer()

# Handle player requests to reveal next phase (flop, turn, river)
@socketio.on('next_phase')
def handle_next_phase():
    if game.phase in ['flop', 'turn', 'river']:
        game.next_phase()
        broadcast_state()

# Reset the game
@socketio.on('reset')
def handle_reset():
    game.reset_game()
    broadcast_state()

if __name__ == '__main__':
    socketio.run(app, debug=True)
    # socketio.run(app, debug=True, host='0.0.0.0')