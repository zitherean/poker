// This file handles UI updates and game state rendering

document.addEventListener('DOMContentLoaded', () => {
    const socket = window.sharedSocket;
    const playerName = window.playerName;

    if (!socket || !playerName) {
        console.error("Socket or playerName not initialized");
        return;
    }

    // === Game functionality ===
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

        // Clear all player name slots
        ['Left', 'Top', 'Right', 'Bottom'].forEach(pos => {
            const el = document.getElementById(`player${pos}`);
            if (el) el.textContent = '';
        });

        // Set player names in their respective positions
        playerEntries.forEach(([sid, player]) => {
            if (player.name === playerName) {
                document.getElementById('playerBottom').textContent = player.name + ' (You)';
            } else if (index < positions.length) {
                const pos = positions[index++];
                const el = document.getElementById(`player${capitalize(pos)}`);
                if (el) el.textContent = player.name;
            }
        });
    });

    // === Helper Functions ===

    // Render cards in the specified container
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

    // Capitalize the first letter of a string
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Check if a card is a red suit
    function isRedSuit(card) {
        const redSuits = [
            "🂱", "🂲", "🂳", "🂴", "🂵", "🂶", "🂷", "🂸", "🂹", "🂺", "🂻", "🂽", "🂾",
            "🃁", "🃂", "🃃", "🃄", "🃅", "🃆", "🃇", "🃈", "🃉", "🃊", "🃋", "🃍", "🃎"
        ];
        return redSuits.includes(card);
    }
});