// Prompt before anything else
let playerName = localStorage.getItem("playerName");
if (!playerName) {
  playerName = prompt("Enter your name:") || "Guest " + Math.floor(Math.random() * 1000);
  localStorage.setItem("playerName", playerName);
}

// Create and share the socket
const socket = io();
window.sharedSocket = socket;
window.playerName = playerName;

// Join the game with the player's name
socket.emit('join', { name: playerName });

// Clean up on exit
window.addEventListener('beforeunload', () => {
  socket.disconnect();
  localStorage.removeItem("playerName");
});