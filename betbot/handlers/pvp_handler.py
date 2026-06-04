from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import session as sess
from games.logic import play_suit, play_coinflip, play_dadu, GAME_INFO

PVP_GAMES = ["suit", "coinflip", "dadu"]
DEFAULT_BET = 100


def _pvp_accept_keyboard(challenger_id: int, target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ TERIMA", callback_data=f"pvp_accept_{challenger_id}_{target_id}"),
        InlineKeyboardButton("❌ TOLAK", callback_data=f"pvp_decline_{challenger_id}_{target_id}"),
    ]])


def _pvp_choice_keyboard(challenger_id: int, target_id: int, game_type: str) -> InlineKeyboardMarkup:
    info = GAME_INFO.get(game_type, {})
    choices = info.get("choices", [])
    buttons = []
    row = []
    for c in choices:
        row.append(InlineKeyboardButton(
            c.upper(),
            callback_data=f"pvp_choice_{challenger_id}_{target_id}_{c}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def pvp_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    db.get_user(user.id, user.username or user.first_name)
    args = context.args

    if len(args) < 1:
        await update.message.reply_text(
            "⚔️ *Format:* `/duel @lawan [mode] [bet]`\n"
            "Contoh: `/duel @budi suit 500`\n\n"
            f"Mode PvP: {', '.join(PVP_GAMES)}",
            parse_mode="Markdown"
        )
        return

    # Parse target
    target_mention = args[0].lstrip("@")
    game_type = args[1].lower() if len(args) > 1 else "suit"
    try:
        bet = int(args[2]) if len(args) > 2 else DEFAULT_BET
    except ValueError:
        bet = DEFAULT_BET

    bet = max(10, min(10000, bet))

    if game_type not in PVP_GAMES:
        await update.message.reply_text(
            f"❌ Mode PvP tidak valid. Pilih: {', '.join(PVP_GAMES)}"
        )
        return

    # Cari target di database
    all_users = db._load()
    target_data = None
    for uid, udata in all_users.items():
        if udata.get("username", "").lower() == target_mention.lower():
            target_data = udata
            break

    if not target_data:
        await update.message.reply_text(
            f"❌ User @{target_mention} tidak ditemukan.\n"
            "Pastikan mereka sudah pakai /start."
        )
        return

    target_id = target_data["user_id"]

    if target_id == user.id:
        await update.message.reply_text("❌ Tidak bisa duel diri sendiri!")
        return

    # Cek saldo challenger
    challenger_data = db.get_user(user.id)
    if challenger_data["coins"] < bet:
        await update.message.reply_text(
            f"❌ Saldo tidak cukup! Butuh *{bet:,} 🪙*, kamu punya *{challenger_data['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
        return

    # Cek saldo target
    if target_data["coins"] < bet:
        await update.message.reply_text(
            f"❌ @{target_mention} tidak punya cukup koin. Saldo mereka: *{target_data['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
        return

    # Buat challenge
    challenge = sess.create_pvp(
        user.id, user.username or user.first_name,
        target_id, target_data["username"],
        game_type, bet, chat.id
    )

    info = GAME_INFO.get(game_type, {})
    msg = await update.message.reply_text(
        f"⚔️ *TANTANGAN DUEL!*\n\n"
        f"🔵 {user.first_name} menantang @{target_data['username']}\n"
        f"🎮 Mode: {info.get('name', game_type)}\n"
        f"💰 Taruhan: *{bet:,} 🪙*\n\n"
        f"@{target_data['username']}, terima tantangan ini?",
        parse_mode="Markdown",
        reply_markup=_pvp_accept_keyboard(user.id, target_id)
    )
    challenge.message_id = msg.message_id


async def pvp_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    parts = query.data.split("_")
    challenger_id = int(parts[2])
    target_id = int(parts[3])

    if user.id != target_id:
        await query.answer("Tantangan ini bukan untukmu!", show_alert=True)
        return

    challenge = sess.get_pvp(challenger_id, target_id)
    if not challenge:
        await query.answer("Tantangan sudah kadaluarsa.", show_alert=True)
        return

    # Cek saldo lagi
    c_data = db.get_user(challenger_id)
    t_data = db.get_user(target_id)

    if c_data["coins"] < challenge.bet:
        await query.edit_message_text(
            f"❌ @{challenge.challenger_name} tidak punya cukup koin lagi."
        )
        sess.delete_pvp(challenger_id, target_id)
        return

    if t_data["coins"] < challenge.bet:
        await query.answer("Saldo kamu tidak cukup!", show_alert=True)
        return

    # Deduct bets
    db.update_coins(challenger_id, -challenge.bet)
    db.update_coins(target_id, -challenge.bet)
    challenge.phase = "playing"

    game_type = challenge.game_type
    info = GAME_INFO.get(game_type, {})

    # Jika dadu, langsung resolve
    if game_type == "dadu":
        await query.answer("✅ Diterima! Game dimulai...")
        await _resolve_pvp_dadu(query, challenge, challenger_id, target_id)
        return

    # Pilihan diperlukan
    players = {
        challenger_id: challenge.challenger_name,
        target_id: challenge.target_name
    }
    await query.edit_message_text(
        f"⚔️ *DUEL DIMULAI!*\n\n"
        f"🔵 {challenge.challenger_name} vs 🔴 {challenge.target_name}\n"
        f"🎮 {info.get('name', game_type)}\n"
        f"💰 {challenge.bet:,} 🪙\n\n"
        f"*{info.get('choice_label', 'Pilih:')}*\n"
        f"_(Kedua pemain harus pilih)_",
        parse_mode="Markdown",
        reply_markup=_pvp_choice_keyboard(challenger_id, target_id, game_type)
    )
    await query.answer("✅ Diterima! Pilih sekarang.")


async def pvp_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    parts = query.data.split("_")
    challenger_id = int(parts[2])
    target_id = int(parts[3])

    # Hanya target atau challenger yang bisa decline
    if user.id not in [challenger_id, target_id]:
        await query.answer("Bukan urusanmu!", show_alert=True)
        return

    challenge = sess.get_pvp(challenger_id, target_id)
    name = challenge.target_name if challenge else "?"
    sess.delete_pvp(challenger_id, target_id)
    await query.edit_message_text(f"❌ Duel ditolak oleh {user.first_name}.")


async def handle_pvp_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if not data.startswith("pvp_choice_"):
        return

    # pvp_choice_{challenger_id}_{target_id}_{choice}
    parts = data.split("_")
    # pvp, choice, challenger_id, target_id, choice_value...
    challenger_id = int(parts[2])
    target_id = int(parts[3])
    choice = "_".join(parts[4:])  # handle multi-word choices

    if user.id not in [challenger_id, target_id]:
        await query.answer("Kamu bukan peserta duel ini!", show_alert=True)
        return

    challenge = sess.get_pvp(challenger_id, target_id)
    if not challenge or challenge.phase != "playing":
        await query.answer("Duel tidak ditemukan.", show_alert=True)
        return

    if user.id in challenge.choices:
        await query.answer("Sudah pilih! Tunggu lawan.", show_alert=True)
        return

    challenge.choices[user.id] = choice
    await query.answer(f"✅ Kamu pilih: {choice.upper()}")

    # Cek apakah kedua pemain sudah pilih
    if challenger_id in challenge.choices and target_id in challenge.choices:
        await _resolve_pvp_choice(query, challenge, challenger_id, target_id)


async def _resolve_pvp_dadu(query, challenge, challenger_id, target_id):
    players = {
        challenger_id: challenge.challenger_name,
        target_id: challenge.target_name
    }
    result = play_dadu(players)
    _apply_pvp_rewards(challenge, result, challenger_id, target_id)
    summary = _pvp_reward_summary(challenge, result, players)
    await query.edit_message_text(
        result["description"] + "\n\n" + summary,
        parse_mode="Markdown"
    )
    sess.delete_pvp(challenger_id, target_id)


async def _resolve_pvp_choice(query, challenge, challenger_id, target_id):
    players = {
        challenger_id: challenge.challenger_name,
        target_id: challenge.target_name
    }
    game_type = challenge.game_type

    if game_type == "suit":
        result = play_suit(challenge.choices, players)
    elif game_type == "coinflip":
        result = play_coinflip(players, challenge.choices)
    else:
        result = {"winner_ids": [], "loser_ids": [], "description": "Error"}

    _apply_pvp_rewards(challenge, result, challenger_id, target_id)
    summary = _pvp_reward_summary(challenge, result, players)
    await query.edit_message_text(
        result["description"] + "\n\n" + summary,
        parse_mode="Markdown"
    )
    sess.delete_pvp(challenger_id, target_id)


def _apply_pvp_rewards(challenge, result, challenger_id, target_id):
    is_draw = result.get("is_draw", False)
    bet = challenge.bet
    winner_ids = result.get("winner_ids", [])

    if is_draw:
        db.update_coins(challenger_id, bet)
        db.update_coins(target_id, bet)
        return

    for uid in winner_ids:
        db.update_coins(uid, bet * 2)  # Bet kembali + winnings
        db.record_win(uid, bet)

    for uid in result.get("loser_ids", []):
        db.record_loss(uid, bet)


def _pvp_reward_summary(challenge, result, players) -> str:
    is_draw = result.get("is_draw", False)
    bet = challenge.bet

    if is_draw:
        return "🤝 *Seri! Koin dikembalikan.*"

    lines = ["💰 *Hasil:*"]
    for uid in result.get("winner_ids", []):
        name = players.get(uid, "?")
        lines.append(f"🏆 {name}: +{bet:,} 🪙 (dapat {bet*2:,} 🪙)")
    for uid in result.get("loser_ids", []):
        name = players.get(uid, "?")
        lines.append(f"💀 {name}: -{bet:,} 🪙")
    return "\n".join(lines)
