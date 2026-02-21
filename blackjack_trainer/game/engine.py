from __future__ import annotations
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class Suit(Enum):
    SPADES   = "♠"
    HEARTS   = "♥"
    DIAMONDS = "♦"
    CLUBS    = "♣"


class Action(Enum):
    HIT    = "hit"
    STAND  = "stand"
    DOUBLE = "double"
    SPLIT  = "split"


class GameResult(Enum):
    WIN       = "win"
    LOSE      = "lose"
    PUSH      = "push"
    BLACKJACK = "blackjack"
    BUST      = "bust"


FACE_CARDS = {"J", "Q", "K"}
ACE = "A"


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: str  # "2"–"10", "J", "Q", "K", "A"

    def __post_init__(self):
        valid = {str(i) for i in range(2, 11)} | FACE_CARDS | {ACE}
        if self.rank not in valid:
            raise ValueError(f"Invalid rank: {self.rank!r}")

    @property
    def value(self) -> int:
        # Ace counts as 11 by default, Hand reduces it when needed
        if self.rank in FACE_CARDS:
            return 10
        if self.rank == ACE:
            return 11
        return int(self.rank)

    @property
    def display(self) -> str:
        return f"{self.rank}{self.suit.value}"

    def __str__(self) -> str:
        return self.display


class Deck:
    """6-deck shoe, standard casino setup."""

    RANKS = [str(i) for i in range(2, 11)] + ["J", "Q", "K", "A"]

    def __init__(self, num_decks: int = 6):
        if num_decks < 1:
            raise ValueError("num_decks must be >= 1")
        self.num_decks = num_decks
        self._cards: List[Card] = []
        self.reshuffle()

    def reshuffle(self) -> None:
        self._cards = [
            Card(suit, rank)
            for _ in range(self.num_decks)
            for suit in Suit
            for rank in self.RANKS
        ]
        random.shuffle(self._cards)

    def deal(self) -> Card:
        # Reshuffle when less than 20% of cards remain
        if len(self._cards) < self.num_decks * 52 * 0.20:
            self.reshuffle()
        return self._cards.pop()

    @property
    def remaining(self) -> int:
        return len(self._cards)

    def __len__(self) -> int:
        return self.remaining


class Hand:
    def __init__(self, cards: Optional[List[Card]] = None):
        self.cards: List[Card] = list(cards) if cards else []

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def calculate_value(self) -> int:
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank == ACE)

        # Reduce each ace from 11 to 1 until we stop busting
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    @property
    def value(self) -> int:
        return self.calculate_value()

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_soft(self) -> bool:
        """Soft hand means an ace is still counting as 11."""
        total = sum(c.value for c in self.cards)
        has_ace = any(c.rank == ACE for c in self.cards)
        return has_ace and total <= 21

    @property
    def is_pair(self) -> bool:
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

    @property
    def can_split(self) -> bool:
        return self.is_pair

    @property
    def can_double(self) -> bool:
        return len(self.cards) == 2

    def split(self) -> Tuple["Hand", "Hand"]:
        if not self.is_pair:
            raise ValueError("Can only split a pair")
        return Hand([self.cards[0]]), Hand([self.cards[1]])

    def __str__(self) -> str:
        cards_str = "  ".join(str(c) for c in self.cards)
        return f"[{cards_str}]  = {self.value}" + (" (soft)" if self.is_soft else "")

    def __len__(self) -> int:
        return len(self.cards)


@dataclass
class RoundState:
    """Snapshot of a round used for DB logging and ML features."""
    player_total: int
    dealer_upcard_value: int
    is_soft: bool
    is_pair: bool
    action_taken: Optional[Action]
    optimal_action: Optional[Action]
    is_correct: Optional[bool]
    result: Optional[GameResult]
    player_cards: List[str]
    dealer_cards: List[str]


class Game:
    """
    Main game loop.

    Usage:
        game = Game()
        game.new_round()
        game.player_action(Action.HIT)
        result = game.dealer_play()
    """

    def __init__(self, num_decks: int = 6):
        self.deck = Deck(num_decks)
        self.player_hand: Optional[Hand] = None
        self.dealer_hand: Optional[Hand] = None
        self._round_active = False
        self._split_hands: List[Hand] = []
        self._current_split_idx: int = 0

    def new_round(self) -> None:
        """Deal initial cards: player gets 2, dealer gets 2 (one face down)."""
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self._split_hands = []
        self._current_split_idx = 0

        # Classic alternating deal: player, dealer, player, dealer
        self.player_hand.add(self.deck.deal())
        self.dealer_hand.add(self.deck.deal())
        self.player_hand.add(self.deck.deal())
        self.dealer_hand.add(self.deck.deal())

        self._round_active = True

    @property
    def dealer_upcard(self) -> Optional[Card]:
        if self.dealer_hand and self.dealer_hand.cards:
            return self.dealer_hand.cards[0]
        return None

    @property
    def round_active(self) -> bool:
        return self._round_active

    def player_action(self, action: Action) -> Optional[GameResult]:
        if not self._round_active:
            raise RuntimeError("Round is not active. Call new_round() first.")

        hand = self._active_hand

        if action == Action.HIT:
            hand.add(self.deck.deal())
            if hand.is_bust:
                self._round_active = False
                return GameResult.BUST

        elif action == Action.STAND:
            if self._split_hands and self._current_split_idx < len(self._split_hands) - 1:
                self._current_split_idx += 1
            else:
                self._round_active = False

        elif action == Action.DOUBLE:
            if not hand.can_double:
                raise ValueError("Double not available after more than 2 cards")
            hand.add(self.deck.deal())
            if hand.is_bust:
                self._round_active = False
                return GameResult.BUST
            self._round_active = False  # auto-stand after double

        elif action == Action.SPLIT:
            if not hand.can_split:
                raise ValueError("Split not available: no pair")
            h1, h2 = hand.split()
            h1.add(self.deck.deal())
            h2.add(self.deck.deal())
            self._split_hands = [h1, h2]
            self._current_split_idx = 0
            self.player_hand = h1

        return None

    @property
    def _active_hand(self) -> Hand:
        if self._split_hands:
            return self._split_hands[self._current_split_idx]
        return self.player_hand  # type: ignore

    def dealer_play(self) -> GameResult:
        """Dealer hits until 17+, then we evaluate the result."""
        hands_to_check = self._split_hands if self._split_hands else [self.player_hand]

        while self.dealer_hand.value < 17:  # type: ignore
            self.dealer_hand.add(self.deck.deal())  # type: ignore

        return self._evaluate(hands_to_check[0])

    def _evaluate(self, player_hand: Hand) -> GameResult:
        dv = self.dealer_hand.value   # type: ignore
        pv = player_hand.value

        if player_hand.is_bust:
            return GameResult.BUST
        if player_hand.is_blackjack and not self.dealer_hand.is_blackjack:  # type: ignore
            return GameResult.BLACKJACK
        if self.dealer_hand.is_blackjack and not player_hand.is_blackjack:  # type: ignore
            return GameResult.LOSE
        if self.dealer_hand.is_bust:  # type: ignore
            return GameResult.WIN
        if pv > dv:
            return GameResult.WIN
        if pv < dv:
            return GameResult.LOSE
        return GameResult.PUSH

    def get_state(self) -> RoundState:
        from game.strategy import get_optimal_action
        ph = self._active_hand
        optimal = get_optimal_action(
            player_total=ph.value,
            dealer_upcard=self.dealer_upcard.value if self.dealer_upcard else 0,
            is_soft=ph.is_soft,
            is_pair=ph.is_pair,
        )
        return RoundState(
            player_total=ph.value,
            dealer_upcard_value=self.dealer_upcard.value if self.dealer_upcard else 0,
            is_soft=ph.is_soft,
            is_pair=ph.is_pair,
            action_taken=None,
            optimal_action=optimal,
            is_correct=None,
            result=None,
            player_cards=[str(c) for c in ph.cards],
            dealer_cards=[str(c) for c in self.dealer_hand.cards] if self.dealer_hand else [],
        )
