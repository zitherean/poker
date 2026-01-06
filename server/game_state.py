# Poker Game State Management
# This module manages the game state for a simple poker game.
# It includes deck creation, shuffling, dealing cards, and player management.

import random

class PokerGame:
    def __init__(self):
        self.deck = self.create_deck()
        self.shuffle_deck()
        self.players = {}  # key: sid, value: {'hand': [...], 'name': ..., 'folded': False}
        self.community_cards = []
        self.pot = 0
        self.phase = 'pre-flop'  # Could be 'pre-flop', 'flop', 'turn', 'river', 'showdown'
        self.turn_order = []       # List of player SIDs (join order)
        self.current_turn = None   # Tracks whose turn it is
        self.acted_players = set()  # Tracks who acted in current round

    # Create a standard deck of cards
    def create_deck(self):
        return [
            "🂡", "🂢", "🂣", "🂤", "🂥", "🂦", "🂧", "🂨", "🂩", "🂪", "🂫", "🂭", "🂮", # Spades
            "🂱", "🂲", "🂳", "🂴", "🂵", "🂶", "🂷", "🂸", "🂹", "🂺", "🂻", "🂽", "🂾", # Hearts
            "🃁", "🃂", "🃃", "🃄", "🃅", "🃆", "🃇", "🃈", "🃉", "🃊", "🃋", "🃍", "🃎", # Diamonds
            "🃑", "🃒", "🃓", "🃔", "🃕", "🃖", "🃗", "🃘", "🃙", "🃚", "🃛", "🃝", "🃞"  # Clubs
        ]

    # Shuffle the deck
    def shuffle_deck(self):
        random.shuffle(self.deck)

    # Deal community cards based on the current phase
    def next_phase(self):
        if self.phase == 'pre-flop':
            self.community_cards = [self.deck.pop() for _ in range(3)]
            self.phase = 'flop'
        elif self.phase == 'flop':
            self.community_cards.append(self.deck.pop())
            self.phase = 'turn'
        elif self.phase == 'turn':
            self.community_cards.append(self.deck.pop())
            self.phase = 'river'

    # Process player actions like folding or betting
    def process_action(self, sid, action):
        if action == 'fold':
            self.players[sid]['folded'] = True
        elif action == 'bet':
            self.pot += 10  # placeholder

        self.acted_players.add(sid)


    # Advance to the next phase of the game
    def advance_turn(self):
        active_players = [sid for sid in self.turn_order if not self.players[sid]['folded']]

        if all(sid in self.acted_players for sid in active_players):
            # Round complete → advance phase
            self.deal_community_cards()
            self.acted_players.clear()
            self.current_turn = active_players[0] if active_players else None
            return

        # Move to the next non-folded player who hasn't acted yet
        current_index = self.turn_order.index(self.current_turn)
        for _ in range(len(self.turn_order)):
            current_index = (current_index + 1) % len(self.turn_order)
            next_sid = self.turn_order[current_index]
            if not self.players[next_sid]['folded'] and next_sid not in self.acted_players:
                self.current_turn = next_sid
                return

    # Reset the game state
    def reset_game(self):
        self.__init__()

    # Add a player to the game
    # Returns True if player was added, False if name is taken or table is full
    def add_player(self, sid, name):
        if name in [p['name'] for p in self.players.values()]:
            return False  # Reject duplicate names
        if sid not in self.players and len(self.players) < 4: # Limit to 4 players
            self.players[sid] = {
                'name': name,
                'hand': [self.deck.pop(), self.deck.pop()],
                'folded': False
            }

            self.turn_order.append(sid)
            if self.current_turn is None:
                self.current_turn = sid

            return True
        return False

    # Get the current game state
    # Returns a dictionary with player hands, community cards, pot, phase and current turn   
    def get_state(self):
        return {
            'players': {sid: {
                'name': player['name'],
                'hand': player['hand']
            } for sid, player in self.players.items()},
            'community_cards': self.community_cards,
            'pot': self.pot,
            'phase': self.phase,
            'current_turn': self.current_turn,
            'current_turn_name': self.players.get(self.current_turn, {}).get('name')
        }