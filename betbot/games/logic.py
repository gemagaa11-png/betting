"""
Logic semua game yang tersedia.
Setiap game return dict berisi: result, winner_ids, description
"""
import random
from typing import Optional


# ============================================================
# COIN FLIP
# ============================================================
def play_coinflip(players: dict[int, str], choices: dict[int, str]) -> dict:
    """
    Choices: "heads" atau "tails"
    Semua yang nebak benar menang, sisanya kalah.
    """
    result = random.choice(["heads", "tails"])
    emoji = "🪙 HEADS" if result == "heads" else "🪙 TAILS"

    winners = [uid for uid, choice in choices.items() if choice == result]
    losers = [uid for uid in players if uid not in winners]

    lines = [f"🎲 *Hasil Coin Flip: {emoji}*\n"]
    for uid, name in players.items():
        choice = choices.get(uid, "?")
        if uid in winners:
            lines.append(f"✅ {name} → {choice.upper()} — MENANG!")
        else:
            lines.append(f"❌ {name} → {choice.upper()} — KALAH")

    return {
        "result": result,
        "winner_ids": winners,
        "loser_ids": losers,
        "description": "\n".join(lines)
    }


# ============================================================
# DADU (1-6)
# ============================================================
def play_dadu(players: dict[int, str]) -> dict:
    """
    Setiap pemain roll dadu. Nilai tertinggi menang.
    Jika seri, semua seri → refund (no winners).
    """
    rolls = {uid: random.randint(1, 6) for uid in players}
    max_val = max(rolls.values())
    top_players = [uid for uid, val in rolls.items() if val == max_val]

    dadu_emoji = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    lines = ["🎲 *Hasil Lempar Dadu!*\n"]
    for uid, name in players.items():
        val = rolls[uid]
        mark = "👑" if uid in top_players and len(top_players) == 1 else ("🤝" if uid in top_players else "💀")
        lines.append(f"{mark} {name} → {dadu_emoji[val]} ({val})")

    if len(top_players) > 1:
        lines.append("\n🤝 *SERI! Koin dikembalikan.*")
        winners = []
        losers = []
    else:
        winners = top_players
        losers = [uid for uid in players if uid not in winners]
        lines.append(f"\n🏆 *{players[winners[0]]} MENANG!*")

    return {
        "rolls": rolls,
        "winner_ids": winners,
        "loser_ids": losers,
        "is_draw": len(top_players) > 1,
        "description": "\n".join(lines)
    }


# ============================================================
# TEBAK ANGKA (1-10)
# ============================================================
def play_tebak_angka(players: dict[int, str], choices: dict[int, str]) -> dict:
    """
    Tebak angka 1-10. Yang tepat menang. Jika tidak ada yang tepat,
    yang paling dekat menang.
    """
    result = random.randint(1, 10)
    int_choices = {}
    for uid, c in choices.items():
        try:
            int_choices[uid] = int(c)
        except (ValueError, TypeError):
            int_choices[uid] = 0

    exact = [uid for uid, val in int_choices.items() if val == result]

    if exact:
        winners = exact
        mode = "exact"
    else:
        # Cari yang paling dekat
        min_diff = min(abs(int_choices.get(uid, 99) - result) for uid in players)
        winners = [uid for uid in players
                   if abs(int_choices.get(uid, 99) - result) == min_diff]
        mode = "closest"

    losers = [uid for uid in players if uid not in winners]

    lines = [f"🔢 *Angka yang keluar: {result}*\n"]
    for uid, name in players.items():
        guess = int_choices.get(uid, "?")
        if uid in winners:
            tag = "🎯 TEPAT!" if mode == "exact" else "🔍 Paling Dekat!"
            lines.append(f"✅ {name} → Tebak {guess} — {tag}")
        else:
            lines.append(f"❌ {name} → Tebak {guess} — MELESET")

    if len(winners) > 1:
        lines.append(f"\n🤝 *Seri! Pot dibagi rata.*")

    return {
        "result": result,
        "winner_ids": winners,
        "loser_ids": losers,
        "mode": mode,
        "description": "\n".join(lines)
    }


# ============================================================
# ROULETTE (merah/hitam/hijau)
# ============================================================
ROULETTE_NUMBERS = {
    0: "🟢",
    1: "🔴", 2: "⚫", 3: "🔴", 4: "⚫", 5: "🔴", 6: "⚫",
    7: "🔴", 8: "⚫", 9: "🔴", 10: "⚫", 11: "⚫", 12: "🔴",
    13: "⚫", 14: "🔴", 15: "⚫", 16: "🔴", 17: "⚫", 18: "🔴",
    19: "🔴", 20: "⚫", 21: "🔴", 22: "⚫", 23: "🔴", 24: "⚫",
    25: "🔴", 26: "⚫", 27: "🔴", 28: "⚫", 29: "⚫", 30: "🔴",
    31: "⚫", 32: "🔴", 33: "⚫", 34: "🔴", 35: "⚫", 36: "🔴"
}

ROULETTE_MULTIPLIERS = {
    "merah": 2,
    "hitam": 2,
    "hijau": 5,  # 0 = hijau, bayar 5x
}


def play_roulette(players: dict[int, str], choices: dict[int, str]) -> dict:
    """
    Pilihan: merah, hitam, hijau (angka 0)
    Hijau bayar 5x, merah/hitam bayar 2x.
    """
    number = random.randint(0, 36)
    color_emoji = ROULETTE_NUMBERS[number]

    if number == 0:
        result_color = "hijau"
    elif color_emoji == "🔴":
        result_color = "merah"
    else:
        result_color = "hitam"

    color_display = {"merah": "🔴 MERAH", "hitam": "⚫ HITAM", "hijau": "🟢 HIJAU (0)"}

    winners = [uid for uid, choice in choices.items() if choice == result_color]
    losers = [uid for uid in players if uid not in winners]
    multiplier = ROULETTE_MULTIPLIERS.get(result_color, 2)

    lines = [f"🎡 *Roulette berhenti di: {number} {color_display[result_color]}*\n"]
    for uid, name in players.items():
        choice = choices.get(uid, "?")
        if uid in winners:
            lines.append(f"✅ {name} → {choice.upper()} — MENANG! ({multiplier}x)")
        else:
            lines.append(f"❌ {name} → {choice.upper()} — KALAH")

    return {
        "number": number,
        "color": result_color,
        "multiplier": multiplier,
        "winner_ids": winners,
        "loser_ids": losers,
        "description": "\n".join(lines)
    }


# ============================================================
# SUIT / GAJAH SEMUT ORANG (RPS versi Indonesia)
# ============================================================
SUIT_BEATS = {
    "gajah": "orang",
    "orang": "semut",
    "semut": "gajah"
}

SUIT_EMOJI = {
    "gajah": "🐘",
    "orang": "🧑",
    "semut": "🐜"
}


def play_suit(choices: dict[int, str], players: dict[int, str]) -> dict:
    """PvP 1v1 suit. Menang → +bet, kalah → -bet, seri → refund."""
    uids = list(choices.keys())
    if len(uids) != 2:
        return {"error": True, "description": "Suit butuh tepat 2 pemain."}

    a, b = uids[0], uids[1]
    ca, cb = choices[a], choices[b]

    lines = [
        f"✊ *SUIT!*\n",
        f"🔵 {players[a]}: {SUIT_EMOJI.get(ca, '?')} {ca.upper()}",
        f"🔴 {players[b]}: {SUIT_EMOJI.get(cb, '?')} {cb.upper()}\n"
    ]

    if ca == cb:
        result = "draw"
        winners = []
        losers = []
        lines.append("🤝 *SERI! Koin dikembalikan.*")
    elif SUIT_BEATS.get(ca) == cb:
        result = "a_wins"
        winners = [a]
        losers = [b]
        lines.append(f"🏆 *{players[a]} MENANG!*")
    else:
        result = "b_wins"
        winners = [b]
        losers = [a]
        lines.append(f"🏆 *{players[b]} MENANG!*")

    return {
        "result": result,
        "winner_ids": winners,
        "loser_ids": losers,
        "is_draw": result == "draw",
        "description": "\n".join(lines)
    }


# ============================================================
# HELPER
# ============================================================
GAME_INFO = {
    "coinflip": {
        "name": "🪙 Coin Flip",
        "desc": "Tebak Heads atau Tails. Yang benar menang.",
        "min_players": 1,
        "max_players": 10,
        "choices": ["heads", "tails"],
        "choice_label": "Pilih sisi koin:"
    },
    "dadu": {
        "name": "🎲 Lempar Dadu",
        "desc": "Semua lempar dadu. Nilai tertinggi menang.",
        "min_players": 2,
        "max_players": 8,
        "choices": [],  # otomatis
        "choice_label": None
    },
    "tebak_angka": {
        "name": "🔢 Tebak Angka",
        "desc": "Tebak angka 1-10. Tepat/paling dekat menang.",
        "min_players": 1,
        "max_players": 10,
        "choices": [str(i) for i in range(1, 11)],
        "choice_label": "Pilih angka (1-10):"
    },
    "roulette": {
        "name": "🎡 Roulette",
        "desc": "Pilih Merah/Hitam/Hijau. Hijau bayar 5x!",
        "min_players": 1,
        "max_players": 10,
        "choices": ["merah", "hitam", "hijau"],
        "choice_label": "Pilih warna:"
    },
    "suit": {
        "name": "✊ Suit (PvP)",
        "desc": "Gajah-Orang-Semut. Khusus 1v1.",
        "min_players": 2,
        "max_players": 2,
        "choices": ["gajah", "orang", "semut"],
        "choice_label": "Pilih:"
    }
}
