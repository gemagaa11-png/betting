"""
Session manager untuk game aktif di setiap grup.
Menyimpan state game di memori (reset jika bot restart).
"""
import time
from typing import Optional

# Format: { chat_id: GameSession }
_active_games: dict = {}

# Format: { chat_id: { user_id: bet_amount } }
_pending_bets: dict = {}

# Format: { f"{from_id}_{to_id}": PvPChallenge }
_pvp_challenges: dict = {}


class GameSession:
    def __init__(self, chat_id: int, game_type: str, host_id: int, bet: int):
        self.chat_id = chat_id
        self.game_type = game_type  # "coinflip", "dadu", "tebak_angka", "roulette", "blackjack_simple"
        self.host_id = host_id
        self.bet = bet
        self.players: dict[int, str] = {}  # {user_id: username}
        self.phase = "waiting"  # waiting → playing → done
        self.created_at = int(time.time())
        self.message_id: Optional[int] = None
        self.game_data: dict = {}  # data spesifik game

    def add_player(self, user_id: int, username: str):
        self.players[user_id] = username

    def remove_player(self, user_id: int):
        self.players.pop(user_id, None)

    def has_player(self, user_id: int) -> bool:
        return user_id in self.players

    def player_count(self) -> int:
        return len(self.players)


class PvPChallenge:
    def __init__(self, challenger_id: int, challenger_name: str,
                 target_id: int, target_name: str,
                 game_type: str, bet: int, chat_id: int):
        self.challenger_id = challenger_id
        self.challenger_name = challenger_name
        self.target_id = target_id
        self.target_name = target_name
        self.game_type = game_type
        self.bet = bet
        self.chat_id = chat_id
        self.created_at = int(time.time())
        self.message_id: Optional[int] = None
        self.phase = "pending"  # pending → playing → done
        self.choices: dict[int, str] = {}  # {user_id: choice}


# === SESSION FUNCTIONS ===

def get_session(chat_id: int) -> Optional[GameSession]:
    return _active_games.get(chat_id)


def create_session(chat_id: int, game_type: str, host_id: int, bet: int) -> GameSession:
    session = GameSession(chat_id, game_type, host_id, bet)
    _active_games[chat_id] = session
    return session


def delete_session(chat_id: int):
    _active_games.pop(chat_id, None)


def has_active_game(chat_id: int) -> bool:
    return chat_id in _active_games


# === PVP FUNCTIONS ===

def get_pvp_key(challenger_id: int, target_id: int) -> str:
    return f"{challenger_id}_{target_id}"


def create_pvp(challenger_id: int, challenger_name: str,
               target_id: int, target_name: str,
               game_type: str, bet: int, chat_id: int) -> PvPChallenge:
    key = get_pvp_key(challenger_id, target_id)
    challenge = PvPChallenge(
        challenger_id, challenger_name,
        target_id, target_name,
        game_type, bet, chat_id
    )
    _pvp_challenges[key] = challenge
    return challenge


def get_pvp(challenger_id: int, target_id: int) -> Optional[PvPChallenge]:
    return _pvp_challenges.get(get_pvp_key(challenger_id, target_id))


def get_pvp_by_target(target_id: int) -> Optional[PvPChallenge]:
    """Cari challenge yang ditujukan ke target_id"""
    for challenge in _pvp_challenges.values():
        if challenge.target_id == target_id and challenge.phase == "pending":
            return challenge
    return None


def delete_pvp(challenger_id: int, target_id: int):
    key = get_pvp_key(challenger_id, target_id)
    _pvp_challenges.pop(key, None)


def cleanup_expired():
    """Hapus session/challenge yang expired (> 10 menit)"""
    now = int(time.time())
    expired_games = [cid for cid, s in _active_games.items()
                     if now - s.created_at > 600]
    for cid in expired_games:
        _active_games.pop(cid, None)

    expired_pvp = [k for k, c in _pvp_challenges.items()
                   if now - c.created_at > 300]
    for k in expired_pvp:
        _pvp_challenges.pop(k, None)
