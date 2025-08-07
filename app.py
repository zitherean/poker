# This file sets up a Flask application with SocketIO for real-time communication.
# It serves an index page and handles incoming messages from clients.

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from server.game_state import PokerGame  # Class is in server/game_state.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Initialize game logic
game = PokerGame()

@app.route('/')
def index():
    return render_template('index.html')

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

# Handle disconnection
@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    player = game.players.pop(sid, None)
    if player:
        print(f"{player['name']} disconnected.")
        socketio.emit('chat', f"❌ {player['name']} has left the game.")
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