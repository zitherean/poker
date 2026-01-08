// static/game.js
document.addEventListener('DOMContentLoaded', () => {
  const socket = window.sharedSocket;
  const playerName = window.playerName;

  if (!socket || !playerName) {
    console.error("Socket or playerName not initialized");
    return;
  }

  let myHand = [];
  let myOptions = {};
  let actionsBound = false;

  // ---- Private: hand + allowed actions ----
  socket.on('private', data => {
    myHand = data.hand || [];
    myOptions = data.options || {};
    renderMyHand();
    updateActionButtons();
  });

  // ---- Public: table state ----
  socket.on('state', data => {
    // community cards
    const communityDiv = document.querySelector('.community-cards');
    if (communityDiv) {
      communityDiv.innerHTML = '';
      renderCards(data.community_cards || [], communityDiv);
    }

    // pot
    const potEl = document.querySelector('.pot');
    if (potEl) potEl.textContent = `Pot: ${data.pot} chips`;

    // turn text
    const turnText = document.getElementById('turnText');
    if (turnText) {
      const name = data.current_turn_name || '—';
      turnText.textContent = (name === playerName) ? "Your turn" : `${name}'s turn`;
    }

    // queued / waiting players (FIXED: inside state handler)
    const waitingEl = document.getElementById('waitingList');
    if (waitingEl) {
      const w = data.waiting || [];
      waitingEl.textContent = w.length ? `Queued: ${w.join(", ")}` : "";
    }

    // Clear labels (removes showdown-injected HTML too)
    ['Left', 'Top', 'Right', 'Bottom'].forEach(pos => {
      const el = document.getElementById(`label${pos}`);
      if (el) el.innerHTML = '';
    });

    // Place players: Bottom = me, others go Left, Top, Right
    const otherSeats = ['Left', 'Top', 'Right'];
    let otherIndex = 0;

    const playerEntries = Object.entries(data.players || {});
    playerEntries.forEach(([sid, p]) => {
      const label = `${p.name}${p.folded ? ' (Folded)' : ''} | ${p.stack} | bet:${p.bet}`;

      if (p.name === playerName) {
        const el = document.getElementById('labelBottom');
        if (el) el.textContent = label + ' (You)';
      } else {
        const seat = otherSeats[otherIndex++];
        if (!seat) return; // table full beyond UI capacity
        const el = document.getElementById(`label${seat}`);
        if (el) el.textContent = label;
      }
    });

    updateDealerChip(data.dealer_name);

    // Bind action buttons once
    if (!actionsBound) {
      actionsBound = true;

      const checkBtn = document.getElementById('checkBtn');
      const betBtn = document.getElementById('betBtn');
      const foldBtn = document.getElementById('foldBtn');

      if (checkBtn) {
        checkBtn.addEventListener('click', () => {
          if (myOptions.check) socket.emit('action', { type: 'check' });
          else socket.emit('action', { type: 'call' });
        });
      }

      if (betBtn) {
        betBtn.addEventListener('click', () => {
          if (myOptions.bet) socket.emit('action', { type: 'bet', amount: myOptions.bet_amount || 10 });
          else socket.emit('action', { type: 'raise', amount: myOptions.raise_by || 10 });
        });
      }

      if (foldBtn) {
        foldBtn.addEventListener('click', () => {
          socket.emit('action', { type: 'fold' });
        });
      }
    }

    updateActionButtons();
  });

  // showdown reveal
  socket.on('showdown', payload => {
    const winners = new Set(payload.winners || []);
    const players = payload.players || {};

    const labelBoxes = {
      Bottom: document.getElementById('labelBottom'),
      Left: document.getElementById('labelLeft'),
      Top: document.getElementById('labelTop'),
      Right: document.getElementById('labelRight'),
    };

    const playerBoxes = {
      Bottom: document.getElementById('playerBottom'),
      Left: document.getElementById('playerLeft'),
      Top: document.getElementById('playerTop'),
      Right: document.getElementById('playerRight'),
    };

    // Clear winner highlight
    Object.values(playerBoxes).forEach(el => el && el.classList.remove('winner'));

    // Rebuild each label area keeping its current label line
    Object.entries(labelBoxes).forEach(([pos, labelEl]) => {
      if (!labelEl) return;
      const currentLabel = labelEl.textContent || '';
      labelEl.innerHTML = `<div>${currentLabel}</div>`;
    });

    // For each player in payload, find their seat by matching name in label text
    for (const [sid, p] of Object.entries(players)) {
      const name = p.name;
      const hand = p.hand || [];
      const best5 = new Set(p.best5 || []);

      const seatPos = Object.keys(labelBoxes).find(pos => {
        const el = labelBoxes[pos];
        return el && el.textContent.includes(name);
      });

      if (!seatPos) continue;

      const labelEl = labelBoxes[seatPos];
      const playerEl = playerBoxes[seatPos];

      if (playerEl && winners.has(sid)) playerEl.classList.add('winner');

      const labelLine = labelEl.textContent;
      labelEl.innerHTML = `
        <div>${labelLine}</div>
        <div class="player-cards" aria-label="revealed cards"></div>
      `;

      const cardsDiv = labelEl.querySelector('.player-cards');
      hand.forEach(card => {
        const cardEl = document.createElement('div');
        cardEl.classList.add('card');
        if (isRedSuit(card)) cardEl.classList.add('red');

        if (winners.has(sid) && best5.has(card)) cardEl.classList.add('win');

        cardEl.textContent = card;
        cardsDiv.appendChild(cardEl);
      });
    }

    const turnText = document.getElementById('turnText');
    if (turnText && payload.message) turnText.textContent = payload.message;
  });

  // timer tick
  socket.on('timer', ({ remaining, current_turn_name }) => {
    const timerEl = document.getElementById('turnTimer');
    if (timerEl) timerEl.textContent = `${remaining}s`;

    const mine = current_turn_name === playerName;
    ['checkBtn', 'betBtn', 'foldBtn'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = !mine;
    });
  });

  function renderMyHand() {
    const handDiv = document.querySelector('.hand');
    if (!handDiv) return;
    handDiv.innerHTML = '';
    renderCards(myHand, handDiv);
  }

  function updateActionButtons() {
    const checkBtn = document.getElementById('checkBtn');
    const betBtn = document.getElementById('betBtn');
    const foldBtn = document.getElementById('foldBtn');

    if (!checkBtn || !betBtn || !foldBtn) return;
    if (!myOptions || Object.keys(myOptions).length === 0) return;

    // Check/Call label
    if (myOptions.check) checkBtn.textContent = 'Check';
    else checkBtn.textContent = `Call ${myOptions.to_call || 0}`;

    // Bet/Raise label + enable/disable
    betBtn.disabled = false;
    if (myOptions.bet) betBtn.textContent = `Bet ${myOptions.bet_amount || 10}`;
    else if (myOptions.raise) betBtn.textContent = `Raise +${myOptions.raise_by || 10}`;
    else betBtn.disabled = true;
  }

  // === Helpers ===
  function renderCards(cards, container) {
    (cards || []).forEach(card => {
      const cardEl = document.createElement('div');
      cardEl.classList.add('card');
      if (isRedSuit(card)) cardEl.classList.add('red');
      cardEl.textContent = card;
      container.appendChild(cardEl);
    });
  }

  function isRedSuit(card) {
    const redSuits = new Set([
      "🂱","🂲","🂳","🂴","🂵","🂶","🂷","🂸","🂹","🂺","🂻","🂽","🂾",
      "🃁","🃂","🃃","🃄","🃅","🃆","🃇","🃈","🃉","🃊","🃋","🃍","🃎"
    ]);
    return redSuits.has(card);
  }

  function updateDealerChip(dealerName) {
    const chipEls = [
      document.getElementById('dealerTop'),
      document.getElementById('dealerLeft'),
      document.getElementById('dealerRight'),
      document.getElementById('dealerBottom'),
    ];
    chipEls.forEach(el => { if (el) el.style.display = 'none'; });

    if (!dealerName) return;

    const seatMap = [
      { label: document.getElementById('labelTop'), chip: document.getElementById('dealerTop') },
      { label: document.getElementById('labelLeft'), chip: document.getElementById('dealerLeft') },
      { label: document.getElementById('labelRight'), chip: document.getElementById('dealerRight') },
      { label: document.getElementById('labelBottom'), chip: document.getElementById('dealerBottom') },
    ];

    const match = seatMap.find(s => s.label && s.label.textContent.includes(dealerName));
    if (match && match.chip) match.chip.style.display = 'block';
  }
});