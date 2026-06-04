import json
import os
import time
from typing import Optional

DATA_FILE = os.environ.get("DATA_FILE", "data/users.json")
STARTING_COINS = 1000
DAILY_REWARD = 200
DAILY_COOLDOWN = 86400  # 24 jam dalam detik


def _load() -> dict:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user(user_id: int, username: str = "") -> dict:
    data = _load()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "user_id": user_id,
            "username": username or f"User{user_id}",
            "coins": STARTING_COINS,
            "wins": 0,
            "losses": 0,
            "last_daily": 0,
            "total_won": 0,
            "total_lost": 0,
            "joined_at": int(time.time())
        }
        _save(data)
    else:
        # update username kalau berubah
        if username and data[uid]["username"] != username:
            data[uid]["username"] = username
            _save(data)
    return data[uid]


def update_coins(user_id: int, delta: int) -> int:
    """Tambah/kurang koin. Return saldo baru."""
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return 0
    data[uid]["coins"] = max(0, data[uid]["coins"] + delta)
    _save(data)
    return data[uid]["coins"]


def set_coins(user_id: int, amount: int):
    data = _load()
    uid = str(user_id)
    if uid in data:
        data[uid]["coins"] = max(0, amount)
        _save(data)


def record_win(user_id: int, amount: int):
    data = _load()
    uid = str(user_id)
    if uid in data:
        data[uid]["wins"] += 1
        data[uid]["total_won"] += amount
        _save(data)


def record_loss(user_id: int, amount: int):
    data = _load()
    uid = str(user_id)
    if uid in data:
        data[uid]["losses"] += 1
        data[uid]["total_lost"] += amount
        _save(data)


def claim_daily(user_id: int):
    """
    Returns: (success, coins_given, seconds_remaining)
    """
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return False, 0, 0
    now = int(time.time())
    last = data[uid].get("last_daily", 0)
    elapsed = now - last
    if elapsed < DAILY_COOLDOWN:
        return False, 0, DAILY_COOLDOWN - elapsed
    data[uid]["last_daily"] = now
    data[uid]["coins"] += DAILY_REWARD
    _save(data)
    return True, DAILY_REWARD, 0


def get_leaderboard(limit: int = 10) -> list[dict]:
    data = _load()
    users = list(data.values())
    users.sort(key=lambda x: x.get("coins", 0), reverse=True)
    return users[:limit]


def transfer_coins(from_id: int, to_id: int, amount: int) -> tuple[bool, str]:
    data = _load()
    fid = str(from_id)
    tid = str(to_id)
    if fid not in data:
        return False, "Akun pengirim tidak ditemukan"
    if tid not in data:
        return False, "Akun penerima tidak ditemukan"
    if data[fid]["coins"] < amount:
        return False, f"Koin tidak cukup. Saldo: {data[fid]['coins']:,} 🪙"
    if amount <= 0:
        return False, "Jumlah harus lebih dari 0"
    data[fid]["coins"] -= amount
    data[tid]["coins"] += amount
    _save(data)
    return True, "ok"


def add_user_if_not_exists(user_id: int, username: str):
    get_user(user_id, username)
