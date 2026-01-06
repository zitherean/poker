# Poker Game State Management
# This module manages the game state for a simple poker game.
# It includes deck creation, shuffling, dealing cards, and player management.

# server/game_state.py
import random
import itertools
from collections import Counter

class PokerGame:
    def __init__(self, starting_stack=200, small_blind=5, big_blind=10):
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind

        self.players = {}      # sid -> dict(name, hand, folded, stack)
        self.turn_order = []   # list of sids in seat order (join order)
        self.dealer_index = 0

        self.reset_hand_state()

        self.hand_start_pending = False

        self.waiting = {}  # (players waiting to be seated next hand)



    # ---------- Deck / Cards ----------
    def create_deck(self):
        return [
            # Spades
            "🂡", "🂢", "🂣", "🂤", "🂥", "🂦", "🂧", "🂨", "🂩", "🂪", "🂫", "🂭", "🂮",
            # Hearts
            "🂱", "🂲", "🂳", "🂴", "🂵", "🂶", "🂷", "🂸", "🂹", "🂺", "🂻", "🂽", "🂾",
            # Diamonds
            "🃁", "🃂", "🃃", "🃄", "🃅", "🃆", "🃇", "🃈", "🃉", "🃊", "🃋", "🃍", "🃎",
            # Clubs
            "🃑", "🃒", "🃓", "🃔", "🃕", "🃖", "🃗", "🃘", "🃙", "🃚", "🃛", "🃝", "🃞"
        ]

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def reset_hand_state(self):
        self.deck = self.create_deck()
        self.shuffle_deck()

        self.community_cards = []
        self.pot = 0
        self.phase = 'waiting'   # waiting, preflop, flop, turn, river, showdown

        self.current_turn = None

        # betting state per street
        self.street_bets = {}     # sid -> amount put in THIS street
        self.current_bet = 0      # highest bet in THIS street
        self.acted = set()        # who has acted since last aggression
        self.last_aggressor = None

        self.last_showdown = None  # message for UI

    # ---------- Players ----------
    def add_player(self, sid, name):
        # name must be unique across seated + waiting
        taken_names = [p['name'] for p in self.players.values()] + list(self.waiting.values())
        if name in taken_names:
            return ("error", "Name taken")

        # if already seated or already waiting
        if sid in self.players:
            return ("ok", "already_seated")
        if sid in self.waiting:
            return ("ok", "already_waiting")

        # table full?
        if len(self.players) >= 4:
            return ("error", "Table full")

        # mid-hand: queue them
        if self.phase in ['preflop', 'flop', 'turn', 'river']:
            self.waiting[sid] = name
            return ("queued", "Game in progress — you’ll join next hand")

        # between hands: seat immediately
        self.players[sid] = {
            'name': name,
            'hand': [],
            'folded': False,
            'stack': self.starting_stack,
        }
        self.turn_order.append(sid)
        return ("ok", "seated")

    def seat_waiting_players(self):
        """Move queued players into the table if seats are available."""
        if not self.waiting:
            return

        for sid, name in list(self.waiting.items()):
            if len(self.players) >= 4:
                break
            # seat them
            self.players[sid] = {
                'name': name,
                'hand': [],
                'folded': False,
                'stack': self.starting_stack,
            }
            self.turn_order.append(sid)
            del self.waiting[sid]

    def remove_player(self, sid):
        if sid not in self.players:
            return None
        player = self.players.pop(sid)
        if sid in self.turn_order:
            idx = self.turn_order.index(sid)
            self.turn_order.pop(idx)
            # adjust dealer index if needed
            if self.turn_order:
                self.dealer_index %= len(self.turn_order)
            else:
                self.dealer_index = 0

        # if hand is running and current turn was them, advance
        if self.current_turn == sid:
            self.advance_turn()

        # if fewer than 2 players remain, stop the hand
        if len(self.active_sids(include_folded=True)) < 2:
            self.reset_hand_state()

        return player

    def active_sids(self, include_folded=False):
        sids = []
        for sid in self.turn_order:
            if sid not in self.players:
                continue
            if self.players[sid]['stack'] <= 0:
                continue
            if (not include_folded) and self.players[sid]['folded']:
                continue
            sids.append(sid)
        return sids

    # ---------- Hand lifecycle ----------
    def start_hand(self):
        # Ensure at least 2 players with chips
        self.seat_waiting_players()

        seats = self.active_sids(include_folded=True)
        if len(seats) < 2:
            self.reset_hand_state()
            return

        # reset hand state but keep players/stacks and turn_order/dealer_index
        self.reset_hand_state()
        self.phase = 'preflop'
        self.last_showdown = None

        # reset per-player hand/folded and street bets
        for sid in self.turn_order:
            if sid in self.players:
                self.players[sid]['folded'] = False
                self.players[sid]['hand'] = []
        self.street_bets = {sid: 0 for sid in self.turn_order if sid in self.players}

        # deal 2 cards each (only players with chips)
        for sid in seats:
            self.players[sid]['hand'] = [self.deck.pop(), self.deck.pop()]

        # post blinds and set turn
        self.post_blinds_and_set_turn()

    def post_blinds_and_set_turn(self):
        seats = self.active_sids(include_folded=True)
        if len(seats) < 2:
            self.phase = 'waiting'
            self.current_turn = None
            return

        # dealer stays as self.dealer_index among turn_order seats
        dealer_sid = self.turn_order[self.dealer_index % len(self.turn_order)]

        # find next active seats for SB/BB
        sb_sid = self.next_active_sid(dealer_sid)
        bb_sid = self.next_active_sid(sb_sid)

        # post SB
        self.pay_into_pot(sb_sid, min(self.small_blind, self.players[sb_sid]['stack']))
        self.street_bets[sb_sid] = min(self.small_blind, self.street_bets.get(sb_sid, 0) + self.small_blind)

        # post BB
        self.pay_into_pot(bb_sid, min(self.big_blind, self.players[bb_sid]['stack']))
        self.street_bets[bb_sid] = min(self.big_blind, self.street_bets.get(bb_sid, 0) + self.big_blind)

        self.current_bet = self.big_blind
        self.last_aggressor = bb_sid
        self.acted = set()

        # preflop action starts left of BB
        self.current_turn = self.next_active_sid(bb_sid)

    def pay_into_pot(self, sid, amount):
        if amount <= 0:
            return 0
        amount = min(amount, self.players[sid]['stack'])
        self.players[sid]['stack'] -= amount
        self.pot += amount
        return amount

    def next_active_sid(self, from_sid):
        """Next seat with chips and not folded (for action)."""
        if not self.turn_order:
            return None
        if from_sid not in self.turn_order:
            start_idx = 0
        else:
            start_idx = self.turn_order.index(from_sid)

        for i in range(1, len(self.turn_order) + 1):
            sid = self.turn_order[(start_idx + i) % len(self.turn_order)]
            if sid in self.players and self.players[sid]['stack'] > 0 and not self.players[sid]['folded']:
                return sid
        return None

    def count_active_not_folded(self):
        return len(self.active_sids(include_folded=False))

    # ---------- Betting rules / actions ----------
    def to_call(self, sid):
        return max(0, self.current_bet - self.street_bets.get(sid, 0))

    def can_check(self, sid):
        return self.to_call(sid) == 0

    def legal_actions(self, sid):
        if sid != self.current_turn:
            return {}

        call_amt = self.to_call(sid)
        stack = self.players[sid]['stack']

        actions = {
            'fold': True,
            'check': call_amt == 0,
            'call': call_amt > 0 and stack >= 0,  # allow call even if it puts them to 0 (we do NOT do side pots in MVP)
            'bet': self.current_bet == 0 and stack > 0,
            'raise': self.current_bet > 0 and stack > call_amt,
        }

        # fixed sizing for simplicity
        actions_meta = {
            'to_call': call_amt,
            'raise_by': self.big_blind,  # raise size step
            'bet_amount': self.big_blind, # bet size step when no bet exists
        }
        return {**actions, **actions_meta}

    def process_action(self, sid, action, amount=None):
        if sid != self.current_turn:
            return False, "Not your turn"
        if sid not in self.players or self.players[sid]['folded']:
            return False, "Invalid player"

        if action == 'fold':
            self.players[sid]['folded'] = True
            self.acted.add(sid)
            return True, None

        if action == 'check':
            if not self.can_check(sid):
                return False, "Cannot check (you must call/fold)"
            self.acted.add(sid)
            return True, None

        if action == 'call':
            call_amt = self.to_call(sid)
            paid = self.pay_into_pot(sid, call_amt)
            self.street_bets[sid] = self.street_bets.get(sid, 0) + paid
            self.acted.add(sid)
            return True, None

        if action == 'bet':
            # only when current_bet == 0
            if self.current_bet != 0:
                return False, "Cannot bet (must call/raise)"
            bet_amt = amount if isinstance(amount, int) and amount > 0 else self.big_blind
            bet_amt = min(bet_amt, self.players[sid]['stack'])
            if bet_amt <= 0:
                return False, "No chips to bet"

            self.pay_into_pot(sid, bet_amt)
            self.street_bets[sid] = self.street_bets.get(sid, 0) + bet_amt
            self.current_bet = self.street_bets[sid]
            self.last_aggressor = sid
            self.acted = {sid}  # reset acted because aggression happened
            return True, None

        if action == 'raise':
            if self.current_bet == 0:
                return False, "Nothing to raise"
            call_amt = self.to_call(sid)
            if self.players[sid]['stack'] <= call_amt:
                return False, "Not enough to raise"

            # fixed raise step: +big_blind unless amount provided
            raise_by = amount if isinstance(amount, int) and amount > 0 else self.big_blind
            target_bet = self.current_bet + raise_by

            # how much total to put in now: (target - already_in)
            need_total = max(0, target_bet - self.street_bets.get(sid, 0))
            need_total = min(need_total, self.players[sid]['stack'])

            if need_total <= 0:
                return False, "Invalid raise"

            self.pay_into_pot(sid, need_total)
            self.street_bets[sid] = self.street_bets.get(sid, 0) + need_total
            self.current_bet = max(self.current_bet, self.street_bets[sid])

            self.last_aggressor = sid
            self.acted = {sid}  # reset acted after aggression
            return True, None

        return False, "Unknown action"

    def betting_round_complete(self):
        active = self.active_sids(include_folded=False)
        if len(active) <= 1:
            return True

        # everyone must have acted since last aggression, and matched current_bet
        for sid in active:
            if sid not in self.acted:
                return False
            if self.street_bets.get(sid, 0) != self.current_bet:
                return False
        return True

    def advance_turn(self):
        # if only one player left, award pot and go to showdown pause
        if self.count_active_not_folded() <= 1 and self.phase in ['preflop', 'flop', 'turn', 'river']:
            self.award_pot_to_last_player()
            self.phase = "showdown"
            self.current_turn = None
            return

        # if betting round complete: move phase / showdown
        if self.phase in ['preflop', 'flop', 'turn', 'river'] and self.betting_round_complete():
            self.advance_phase()
            return

        next_sid = self.next_active_sid(self.current_turn)
        self.current_turn = next_sid


    def reset_street_bets(self):
        for sid in self.street_bets:
            self.street_bets[sid] = 0
        self.current_bet = 0
        self.acted = set()
        self.last_aggressor = None

    def first_to_act_postflop(self):
        dealer_sid = self.turn_order[self.dealer_index % len(self.turn_order)]
        return self.next_active_sid(dealer_sid)

    def advance_phase(self):
        # deal community cards and move to next street
        if self.phase == 'preflop':
            self.community_cards = [self.deck.pop() for _ in range(3)]
            self.phase = 'flop'
        elif self.phase == 'flop':
            self.community_cards.append(self.deck.pop())
            self.phase = 'turn'
        elif self.phase == 'turn':
            self.community_cards.append(self.deck.pop())
            self.phase = 'river'
        elif self.phase == 'river':
            self.phase = 'showdown'
            self.handle_showdown()
            # DO NOT start next hand here. App will start it after 10s.
            self.current_turn = None
            return

        # new betting street
        self.reset_street_bets()
        self.current_turn = self.first_to_act_postflop()

    def rotate_dealer(self):
        if self.turn_order:
            self.dealer_index = (self.dealer_index + 1) % len(self.turn_order)

    def start_next_hand_after_showdown(self):
        self.rotate_dealer()
        self.start_hand()

    def award_pot_to_last_player(self):
        active = self.active_sids(include_folded=False)
        if not active:
            return
        winner = active[0]

        self.players[winner]['stack'] += self.pot
        self.last_showdown = f"{self.players[winner]['name']} wins {self.pot} (everyone else folded)"

        # Reveal hole cards for everyone (same as showdown)
        self.last_showdown_payload = {
            "winners": [winner],
            "players": {
                sid: {
                    "name": self.players[sid]["name"],
                    "hand": self.players[sid]["hand"],
                    "best5": []  # optional for fold-win
                } for sid in self.players.keys()
            },
            "community_cards": self.community_cards,
            "message": self.last_showdown
        }

        self.pot = 0


    # ---------- Public / Private state ----------
    def get_public_state(self):
        dealer_sid = self.turn_order[self.dealer_index % len(self.turn_order)] if self.turn_order else None
        return {
            'players': {
                sid: {
                    'name': p['name'],
                    'folded': p['folded'],
                    'stack': p['stack'],
                    'bet': self.street_bets.get(sid, 0),
                } for sid, p in self.players.items()
            },
            'waiting': list(self.waiting.values()),
            'community_cards': self.community_cards,
            'pot': self.pot,
            'phase': self.phase,
            'current_turn': self.current_turn,
            'current_turn_name': self.players.get(self.current_turn, {}).get('name'),
            'dealer_name': self.players.get(dealer_sid, {}).get('name') if dealer_sid else None,
            'small_blind': self.small_blind,
            'big_blind': self.big_blind,
            'last_showdown': self.last_showdown,
        }

    def get_private_state(self, sid):
        # what ONLY that user should see
        if sid not in self.players:
            return {}
        options = self.legal_actions(sid) if self.phase in ['preflop', 'flop', 'turn', 'river'] else {}
        return {
            'hand': self.players[sid]['hand'],
            'options': options
        }

    # ---------- Hand evaluation ----------
    # Mapping unicode card -> (rank, suit)
    # ranks: 2..14 (Ace=14)
    def _card_to_rank_suit(self, c):
        # Spades 🂡..🂮, Hearts 🂱..🂾, Diamonds 🃁..🃎, Clubs 🃑..🃞
        # Use unicode codepoint blocks.
        code = ord(c)

        # helper to map within each suit block:
        # Order inside block: A,2,3,4,5,6,7,8,9,10,J,Q,K
        # There is a "Knight" in tarot decks for some sets; standard playing cards skip it.
        def map_offset(offset):
            # offset 0->A, 1->2 ... 9->10, 10->J, 11->Q, 12->K
            if offset == 0: return 14
            return offset + 1

        # Spades block starts at U+1F0A1
        if 0x1F0A1 <= code <= 0x1F0AE:
            # skip U+1F0AC (Knight) if present; our deck doesn't include it
            offset = code - 0x1F0A1
            rank = map_offset(offset if offset < 11 else offset - 1)  # adjust after knight position
            return rank, 'S'

        # Hearts starts U+1F0B1
        if 0x1F0B1 <= code <= 0x1F0BE:
            offset = code - 0x1F0B1
            rank = map_offset(offset if offset < 11 else offset - 1)
            return rank, 'H'

        # Diamonds starts U+1F0C1
        if 0x1F0C1 <= code <= 0x1F0CE:
            offset = code - 0x1F0C1
            rank = map_offset(offset if offset < 11 else offset - 1)
            return rank, 'D'

        # Clubs starts U+1F0D1
        if 0x1F0D1 <= code <= 0x1F0DE:
            offset = code - 0x1F0D1
            rank = map_offset(offset if offset < 11 else offset - 1)
            return rank, 'C'

        raise ValueError(f"Unknown card: {c}")

    def _rank_5(self, five_cards):
        ranks = []
        suits = []
        for c in five_cards:
            r, s = self._card_to_rank_suit(c)
            ranks.append(r)
            suits.append(s)

        ranks.sort(reverse=True)
        counts = Counter(ranks)
        count_vals = sorted(counts.values(), reverse=True)
        unique = sorted(counts.keys(), reverse=True)

        is_flush = len(set(suits)) == 1

        # straight detection (handle wheel A-2-3-4-5)
        distinct = sorted(set(ranks), reverse=True)
        is_straight = False
        straight_high = None
        if len(distinct) == 5:
            if distinct[0] - distinct[4] == 4:
                is_straight = True
                straight_high = distinct[0]
            elif distinct == [14, 5, 4, 3, 2]:
                is_straight = True
                straight_high = 5

        # category: 8 straight flush, 7 quads, 6 full house, 5 flush, 4 straight, 3 trips, 2 two pair, 1 pair, 0 high
        if is_straight and is_flush:
            return (8, [straight_high])

        if count_vals == [4, 1]:
            quad = max([r for r, c in counts.items() if c == 4])
            kicker = max([r for r, c in counts.items() if c == 1])
            return (7, [quad, kicker])

        if count_vals == [3, 2]:
            trips = max([r for r, c in counts.items() if c == 3])
            pair = max([r for r, c in counts.items() if c == 2])
            return (6, [trips, pair])

        if is_flush:
            return (5, ranks)

        if is_straight:
            return (4, [straight_high])

        if count_vals == [3, 1, 1]:
            trips = max([r for r, c in counts.items() if c == 3])
            kickers = sorted([r for r, c in counts.items() if c == 1], reverse=True)
            return (3, [trips] + kickers)

        if count_vals == [2, 2, 1]:
            pairs = sorted([r for r, c in counts.items() if c == 2], reverse=True)
            kicker = max([r for r, c in counts.items() if c == 1])
            return (2, pairs + [kicker])

        if count_vals == [2, 1, 1, 1]:
            pair = max([r for r, c in counts.items() if c == 2])
            kickers = sorted([r for r, c in counts.items() if c == 1], reverse=True)
            return (1, [pair] + kickers)

        return (0, ranks)

    def best_hand_rank(self, seven_cards):
        best = None
        best_combo = None
        for combo in itertools.combinations(seven_cards, 5):
            r = self._rank_5(combo)
            if best is None or r > best:
                best = r
                best_combo = list(combo)
        return best, best_combo

    def handle_showdown(self):
        self.last_showdown_payload = None

        active = self.active_sids(include_folded=False)
        if not active:
            self.pot = 0
            self.last_showdown = "No active players at showdown."
            self.last_showdown_payload = {
                "winners": [],
                "players": {}
            }
            return

        ranks = {}
        best5 = {}
        for sid in active:
            seven = self.players[sid]['hand'] + self.community_cards
            r, combo = self.best_hand_rank(seven)
            ranks[sid] = r
            best5[sid] = combo or []

        best_rank = max(ranks.values())
        winners = [sid for sid, r in ranks.items() if r == best_rank]

        # Pay pot (MVP: no side pots)
        if len(winners) == 1:
            w = winners[0]
            self.players[w]['stack'] += self.pot
            self.last_showdown = f"{self.players[w]['name']} wins {self.pot} at showdown"
        else:
            share = self.pot // len(winners)
            remainder = self.pot % len(winners)
            for i, sid in enumerate(winners):
                self.players[sid]['stack'] += share + (1 if i < remainder else 0)
            names = ", ".join(self.players[s]['name'] for s in winners)
            self.last_showdown = f"Split pot {self.pot} between: {names}"

        # Build payload for UI reveal
        self.last_showdown_payload = {
            "winners": winners,
            "players": {
                sid: {
                    "name": self.players[sid]["name"],
                    "hand": self.players[sid]["hand"],
                    "best5": best5.get(sid, [])
                } for sid in self.players.keys()  # include folded too, so all hands reveal (or you can choose only active)
            },
            "community_cards": self.community_cards,
            "message": self.last_showdown
        }

        self.pot = 0
