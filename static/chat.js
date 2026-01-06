// This file handles chat functionality in the poker game

document.addEventListener('DOMContentLoaded', () => {
  const socket = window.sharedSocket;
  const playerName = window.playerName;

  if (!socket || !playerName) {
    console.error("Socket or playerName not initialized");
    return;
  }

  // === Chat functionality ===
  const sendBtn = document.getElementById('sendBtn');
  const chatInput = document.getElementById('chatInput');
  const messages = document.getElementById('messages');

  // Click event for send button
  sendBtn.addEventListener('click', () => {
      const msg = chatInput.value;
      if (msg.trim() !== '') {
        socket.emit('chat', { user: playerName, msg });
        chatInput.value = '';
      }
  });

  // Keydown event for Enter key
  chatInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        sendBtn.click();
      }
  });

  // Listen for incoming chat messages
  socket.on('chat', data => {
    const msgDiv = document.createElement('div');

    // data can be {user, msg} or a plain string (fallback)
    if (typeof data === 'string') {
      msgDiv.textContent = data;
    } else {
      const user = data.user ?? 'Unknown';
      const msg = data.msg ?? '';
      msgDiv.textContent = `${user}: ${msg}`;
    }

    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;
  });

  socket.on('error', (data) => {
    if (!data) return;
    const text = data.chat || data.message || JSON.stringify(data);
    // show it in chat area instead of alert if you want
    console.log("Server:", text);
  });

});