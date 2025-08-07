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
    def deal_community_cards(self):
        if self.phase == 'pre-flop':
            self.community_cards = [self.deck.pop() for _ in range(3)]
            self.phase = 'flop'
        elif self.phase == 'flop':
            self.community_cards.append(self.deck.pop())
            self.phase = 'turn'
        elif self.phase == 'turn':
            self.community_cards.append(self.deck.pop())
            self.phase = 'river'

    # Reset the game state
    def reset(self):
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
            return True
        return False

    # Get the current game state
    # Returns a dictionary with player hands, community cards, pot, and phase
    def get_state(self):
        return {
            'players': {sid: {
                'name': player['name'],
                'hand': player['hand']
            } for sid, player in self.players.items()},
            'community_cards': self.community_cards,
            'pot': self.pot,
            'phase': self.phase
        }