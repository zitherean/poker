// This file handles UI updates and game state rendering

// static/game.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = window.sharedSocket;
    const playerName = window.playerName;

    if (!socket || !playerName) {
        console.error("Socket or playerName not initialized");
        return;
    }

    let actionsBound = false;

    socket.on('state', data => {
        console.log("Game state received:", data);

        // Display player's hand
        const handDiv = document.querySelector('.hand');
        handDiv.innerHTML = '';
        const playerData = Object.values(data.players).find(p => p.name === playerName);
        if (playerData) {
            renderCards(playerData.hand, handDiv);
        }

        // Display community cards
        const communityDiv = document.querySelector('.community-cards');
        communityDiv.innerHTML = '';
        renderCards(data.community_cards, communityDiv);

        // Display player names
        const positions = ['left', 'top', 'right'];
        const playerEntries = Object.entries(data.players);
        let index = 0;
        ['Left', 'Top', 'Right', 'Bottom'].forEach(pos => {
            const el = document.getElementById(`player${pos}`);
            if (el) el.textContent = '';
        });
        playerEntries.forEach(([sid, player]) => {
            if (player.name === playerName) {
                document.getElementById('playerBottom').textContent = player.name + ' (You)';
            } else if (index < positions.length) {
                const pos = positions[index++];
                const el = document.getElementById(`player${capitalize(pos)}`);
                if (el) el.textContent = player.name;
            }
        });

        // Show whose turn it is
        const turnText = document.getElementById('turnText');
        if (turnText) {
            const name = data.current_turn_name || '—';
            turnText.textContent = (name === playerName) ? "Your turn" : `${name}'s turn`;
        }

        // Bind action buttons once
        if (!actionsBound) {
            actionsBound = true;
            document.getElementById('checkBtn').addEventListener('click', () => {
                socket.emit('action', { type: 'check' });
            });
            document.getElementById('betBtn').addEventListener('click', () => {
                socket.emit('action', { type: 'bet' });
            });
            document.getElementById('foldBtn').addEventListener('click', () => {
                socket.emit('action', { type: 'fold' });
            });
        }
    });

    // Receive per-second ticks
    socket.on('timer', ({ remaining, current_turn_name }) => {
        const timerEl = document.getElementById('turnTimer');
        if (timerEl) timerEl.textContent = `${remaining}s`;
        const turnText = document.getElementById('turnText');
        if (turnText) {
            turnText.textContent = (current_turn_name === playerName) ? "Your turn" : `${current_turn_name}'s turn`;
        }

        // Optionally disable buttons when it's not your turn
        const mine = current_turn_name === playerName;
        ['checkBtn','betBtn','foldBtn'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = !mine;
        });
    });

    // === Helper Functions ===
    function renderCards(cards, container) {
        cards.forEach(card => {
            const cardEl = document.createElement('div');
            cardEl.classList.add('card');
            if (isRedSuit(card)){
                cardEl.classList.add('red');
            }
            cardEl.textContent = card;
            container.appendChild(cardEl);
        });
    }
    function capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }
    function isRedSuit(card) {
        const redSuits = [
            "🂱","🂲","🂳","🂴","🂵","🂶","🂷","🂸","🂹","🂺","🂻","🂽","🂾",
            "🃁","🃂","🃃","🃄","🃅","🃆","🃇","🃈","🃉","🃊","🃋","🃍","🃎"
        ];
        return redSuits.includes(card);
    }
});