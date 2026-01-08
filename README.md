# 🃏 Online Poker Game (MVP)

A **browser-based Texas Hold’em poker game** built as a personal project for learning and fun, using **Flask** and **Socket.IO** for real-time multiplayer gameplay.

👉 **Launch App:** https://poker-1303.onrender.com

The game runs entirely in the browser and manages all poker logic on the server, with live updates sent via WebSockets.

---

## ✨ Features

- Real-time multiplayer gameplay  
- Server-side game state & betting logic  
- Turn timers with automatic fold on timeout  
- Blinds, betting rounds, and dealer rotation  
- Community cards and showdown hand evaluation  
- Simple, responsive UI (HTML / CSS / JS)

---

## ⚠️ MVP Disclaimer

This project is a **Minimum Viable Product (MVP)** and is intentionally simplified.

Some poker features are **not implemented**, including:
- All-in handling  
- Side pots  
- Full split-pot logic  
- Advanced bet sizing  
- Player accounts or reconnection handling  

Expect rough edges. This is a learning project, not production software.

---

## ▶️ Run locally

```bash
pip install flask flask-socketio
python app.py
````

Open `http://127.0.0.1:5000` and use multiple tabs or browsers to test multiplayer.

---

Built for learning, experimenting, and playing with friends. Not for real money.
