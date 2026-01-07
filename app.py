# This file sets up a Flask application with SocketIO for real-time communication.
# It serves an index page and handles incoming messages from clients.
# app.py
import time
import os
from threading import Lock
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from server.game_state import PokerGame

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

game = PokerGame(starting_stack=200, small_blind=5, big_blind=10)

@app.route('/')
def index():
    return render_template('index.html')

TURN_SECONDS = 30
SHOWDOWN_SECONDS = 10
timer_lock = Lock()
turn_token = 0
turn_expires_at = None

START_DELAY_SECONDS = 10
start_lock = Lock()
start_token = 0


def broadcast_state():
    socketio.emit('state', game.get_public_state())

    for sid in list(game.players.keys()):
        socketio.emit('private', game.get_private_state(sid), to=sid)

    # If we're in showdown, also send reveal payload
    if getattr(game, "phase", None) == "showdown" and getattr(game, "last_showdown_payload", None):
        socketio.emit('showdown', game.last_showdown_payload)

def start_turn_timer():
    global turn_token, turn_expires_at

    with timer_lock:
        # Invalidate any existing timers
        turn_token += 1
        my_token = turn_token 

        # Do not run timers during showdown
        if game.phase == "showdown":
            turn_expires_at = None
            return

        # Start timer only if someone has the turn
        if game.current_turn:
            turn_expires_at = time.time() + TURN_SECONDS
        else:
            turn_expires_at = None
            return

        def _tick(): 
            while True:
                with timer_lock:
                    if my_token != turn_token:
                        return

                    remaining = max(0, int(turn_expires_at - time.time()))
                    current_name = game.players.get(game.current_turn, {}).get('name')

                    socketio.emit('timer', {
                        'remaining': remaining,
                        'current_turn_name': current_name
                    })

                    if remaining == 0:
                        sid = game.current_turn
                        if sid and sid in game.players and not game.players[sid]['folded']:
                            ok, err = game.process_action(sid, 'fold')
                            if not ok:
                                print("Auto-fold failed:", err)

                        game.advance_turn()
                        broadcast_state()

                        if game.phase == "showdown":
                            schedule_next_hand()
                            return

                        start_turn_timer()
                        return

                socketio.sleep(1)

        socketio.start_background_task(_tick)

def maybe_schedule_hand_start():
    global start_token
    with start_lock:
        # Only schedule if waiting, at least 2 players, and not already running
        if game.phase != "waiting":
            return
        if len(game.players) < 2:
            return

        start_token += 1
        my_token = start_token

        def _start_later():
            socketio.sleep(START_DELAY_SECONDS)
            with start_lock:
                if my_token != start_token:
                    return
                if game.phase == "waiting" and len(game.players) >= 2:
                    game.start_hand()
                    broadcast_state()
                    start_turn_timer()

        socketio.start_background_task(_start_later)


@socketio.on('join')
def handle_join(data):
    name = data.get('name', 'Guest')
    sid = request.sid

    status, msg = game.add_player(sid, name)

    if status == "error":
        emit('error', {'chat': msg}, to=sid)
        return

    if status == "queued":
        emit('error', {'chat': msg}, to=sid)  # or emit('chat', ...) just to them
        broadcast_state()
        return

    # seated
    socketio.emit('chat', f"🔔 {name} has joined the game.")
    broadcast_state()

    # if between hands and >=2 players, schedule start
    maybe_schedule_hand_start()
    start_turn_timer()


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    player = game.remove_player(sid)
    if player:
        socketio.emit('chat', f"❌ {player['name']} has left the game.")
        broadcast_state()
        start_turn_timer()

@socketio.on('chat')
def handle_chat(data):
    user = (data or {}).get('user', 'Unknown')
    msg = (data or {}).get('msg', '')
    msg = msg.strip()
    if not msg:
        return

    socketio.emit('chat', {
        'user': user,
        'msg': msg
    })

@socketio.on('action')
def handle_action(data):
    sid = request.sid
    action = data.get('type')
    amount = data.get('amount')  # optional int for bet/raise sizes

    ok, err = game.process_action(sid, action, amount=amount)
    if not ok:
        emit('error', {'message': err}, to=sid)
        return

    game.advance_turn()
    broadcast_state()

    # If showdown, wait 10 seconds then start next hand
    if game.phase == "showdown":
        schedule_next_hand()
        return

    start_turn_timer()

def schedule_next_hand():
    def _resume():
        socketio.sleep(SHOWDOWN_SECONDS)
        if len(game.players) >= 2:
            game.start_next_hand_after_showdown()
            broadcast_state()
            start_turn_timer()
    socketio.start_background_task(_resume)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
