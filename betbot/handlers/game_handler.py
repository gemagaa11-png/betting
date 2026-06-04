from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import session as sess
from games.logic import (
    play_coinflip, play_dadu, play_tebak_angka, play_roulette,
    GAME_INFO
)

DEFAULT_BET = 100
MAX_BET = 10000
MIN_BET = 10


def _game_keyboard(game_type: str, phase: str = "waiting") -> InlineKeyboardMarkup:
    if phase == "waiting":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ JOIN", callback_data="join_game"),
            InlineKeyboardButton("🚪 LEAVE", callback_data="leave_game"),
        ], [
            InlineKeyboardButton("▶️ MULAI", callback_data="start_round"),
            InlineKeyboardButton("❌ CANCEL", callback_data="cancel_game"),
        ]])
    return InlineKeyboardMarkup([])


def _choice_keyboard(game_type: str) -> InlineKeyboardMarkup:
    info = GAME_INFO.get(game_type, {})
    choices = info.get("choices", [])
    if not choices:
        return InlineKeyboardMarkup([])

    buttons = []
    row = []
    for i, c in enumerate(choices):
        row.append(InlineKeyboardButton(c.upper(), callback_data=f"game_choice_{c}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _lobby_text(session: sess.GameSession) -> str:
    info = GAME_INFO.get(session.game_type, {})
    lines = [
        f"🎰 *GAME DIBUKA: {info.get('name', session.game_type)}*",
        f"📋 {info.get('desc', '')}",
        f"💰 Taruhan: *{session.bet:,} 🪙 per ronde*\n",
        f"👥 Pemain ({session.player_count()}):"
    ]
    if session.players:
        for uid, name in session.players.items():
            lines.append(f"  • {name}")
    else:
        lines.append("  _(belum ada)_")

    lines.append(f"\nKlik *JOIN* untuk ikut, *MULAI* bila sudah siap.")
    return "\n".join(lines)


async def game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    db.get_user(user.id, user.username or user.first_name)

    if chat.type == "private":
        await update.message.reply_text(
            "⚠️ Game grup harus dimainkan di grup Telegram.\n"
            "Untuk PvP gunakan /duel."
        )
        return

    args = context.args

    if not args:
        # Tampilkan menu pilihan game
        kb = []
        for key, info in GAME_INFO.items():
            if key == "suit":
                continue  # suit khusus pvp
            kb.append([InlineKeyboardButton(
                f"{info['name']} — min {DEFAULT_BET}🪙",
                callback_data=f"game_open_{key}_{DEFAULT_BET}"
            )])
        kb.append([InlineKeyboardButton("❓ Panduan", callback_data="game_help")])
        await update.message.reply_text(
            "🎰 *Pilih mode game:*\n\nAtau gunakan:\n`/game [mode] [bet]`\nContoh: `/game dadu 200`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    game_type = args[0].lower()
    if game_type not in GAME_INFO or game_type == "suit":
        valid = ", ".join(k for k in GAME_INFO if k != "suit")
        await update.message.reply_text(f"❌ Mode tidak valid. Pilih: {valid}")
        return

    try:
        bet = int(args[1]) if len(args) > 1 else DEFAULT_BET
    except ValueError:
        bet = DEFAULT_BET

    bet = max(MIN_BET, min(MAX_BET, bet))
    await _open_game(update, context, user, chat.id, game_type, bet)


async def _open_game(update, context, user, chat_id, game_type, bet):
    if sess.has_active_game(chat_id):
        existing = sess.get_session(chat_id)
        info = GAME_INFO.get(existing.game_type, {})
        await update.message.reply_text(
            f"⚠️ Sudah ada game aktif: *{info.get('name', existing.game_type)}*\n"
            f"Ketik /cancel untuk membatalkan dulu.",
            parse_mode="Markdown"
        )
        return

    # Cek saldo
    data = db.get_user(user.id)
    if data["coins"] < bet:
        await update.message.reply_text(
            f"❌ Saldo tidak cukup. Butuh *{bet:,} 🪙*, kamu punya *{data['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
        return

    session = sess.create_session(chat_id, game_type, user.id, bet)
    session.add_player(user.id, user.username or user.first_name)

    msg = await update.message.reply_text(
        _lobby_text(session),
        parse_mode="Markdown",
        reply_markup=_game_keyboard(game_type, "waiting")
    )
    session.message_id = msg.message_id


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user = query.from_user
        chat_id = query.message.chat_id
        msg = query.message
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id
        msg = None

    db.get_user(user.id, user.username or user.first_name)
    session = sess.get_session(chat_id)

    if not session:
        text = "⚠️ Tidak ada game aktif. Buka dengan /game [mode] [bet]"
        if query:
            await query.answer(text, show_alert=True)
        else:
            await update.message.reply_text(text)
        return

    if session.phase != "waiting":
        text = "⚠️ Game sudah berjalan!"
        if query:
            await query.answer(text, show_alert=True)
        return

    if session.has_player(user.id):
        if query:
            await query.answer("Kamu sudah join!", show_alert=True)
        return

    # Cek saldo
    data = db.get_user(user.id)
    if data["coins"] < session.bet:
        text = f"❌ Saldo tidak cukup! Butuh {session.bet:,} 🪙"
        if query:
            await query.answer(text, show_alert=True)
        return

    session.add_player(user.id, user.username or user.first_name)

    if query:
        await query.edit_message_text(
            _lobby_text(session),
            parse_mode="Markdown",
            reply_markup=_game_keyboard(session.game_type, "waiting")
        )
        await query.answer(f"✅ Kamu join! Taruhan: {session.bet:,} 🪙")
    elif update.message:
        await update.message.reply_text(f"✅ {user.first_name} join game!")


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user = query.from_user
        chat_id = query.message.chat_id
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id

    session = sess.get_session(chat_id)
    if not session or not session.has_player(user.id):
        if query:
            await query.answer("Kamu tidak dalam game.", show_alert=True)
        return

    if session.phase != "waiting":
        if query:
            await query.answer("Game sudah dimulai!", show_alert=True)
        return

    session.remove_player(user.id)

    # Jika host leave, cancel game
    if user.id == session.host_id:
        sess.delete_session(chat_id)
        if query:
            await query.edit_message_text("❌ Game dibatalkan (host keluar).")
        return

    if query:
        await query.edit_message_text(
            _lobby_text(session),
            parse_mode="Markdown",
            reply_markup=_game_keyboard(session.game_type, "waiting")
        )
        await query.answer("Kamu keluar dari game.")


async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user = query.from_user
        chat_id = query.message.chat_id
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id

    session = sess.get_session(chat_id)
    if not session:
        text = "Tidak ada game aktif."
        if query:
            await query.answer(text, show_alert=True)
        else:
            await update.message.reply_text(text)
        return

    # Cek admin atau host
    is_host = session.host_id == user.id
    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        is_admin = member.status in ["administrator", "creator"]
    except Exception:
        is_admin = False

    if not (is_host or is_admin):
        if query:
            await query.answer("Hanya host atau admin yang bisa cancel.", show_alert=True)
        else:
            await update.message.reply_text("❌ Hanya host atau admin yang bisa cancel.")
        return

    sess.delete_session(chat_id)
    if query:
        await query.edit_message_text("❌ Game dibatalkan.")
    else:
        await update.message.reply_text("❌ Game dibatalkan.")


async def start_round(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user = query.from_user
        chat_id = query.message.chat_id
        msg_obj = query.message
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id
        msg_obj = None

    session = sess.get_session(chat_id)
    if not session:
        if query:
            await query.answer("Tidak ada game aktif.", show_alert=True)
        return

    is_host = session.host_id == user.id
    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        is_admin = member.status in ["administrator", "creator"]
    except Exception:
        is_admin = False

    if not (is_host or is_admin):
        if query:
            await query.answer("Hanya host/admin yang bisa mulai game.", show_alert=True)
        return

    info = GAME_INFO.get(session.game_type, {})
    min_p = info.get("min_players", 1)

    if session.player_count() < min_p:
        txt = f"⚠️ Butuh minimal {min_p} pemain! Sekarang: {session.player_count()}"
        if query:
            await query.answer(txt, show_alert=True)
        return

    # Deduct bets
    insufficient = []
    for uid in list(session.players.keys()):
        data = db.get_user(uid)
        if data["coins"] < session.bet:
            insufficient.append(session.players[uid])
            session.remove_player(uid)

    if insufficient:
        names = ", ".join(insufficient)
        await context.bot.send_message(
            chat_id,
            f"⚠️ {names} tidak punya cukup koin dan dikeluarkan dari game."
        )

    if session.player_count() < min_p:
        sess.delete_session(chat_id)
        await context.bot.send_message(chat_id, "❌ Game dibatalkan karena pemain tidak cukup.")
        return

    # Deduct semua bet
    for uid in session.players:
        db.update_coins(uid, -session.bet)

    session.phase = "playing"
    session.game_data["choices"] = {}

    game_type = session.game_type
    choices = info.get("choices", [])

    if game_type == "dadu":
        # Dadu langsung main, tidak perlu pilih
        await _resolve_dadu(query, context, session, chat_id)
        return

    # Game yang butuh pilihan pemain
    label = info.get("choice_label", "Pilih:")
    players_list = "\n".join(f"• {n}" for n in session.players.values())
    text = (
        f"🎮 *Game dimulai!*\n\n"
        f"Mode: {info.get('name')}\n"
        f"Taruhan: {session.bet:,} 🪙\n\n"
        f"👥 Pemain:\n{players_list}\n\n"
        f"*{label}*\n_(Setiap pemain pilih via tombol di bawah)_"
    )

    if query:
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=_choice_keyboard(game_type)
        )
    else:
        await context.bot.send_message(
            chat_id, text, parse_mode="Markdown",
            reply_markup=_choice_keyboard(game_type)
        )


async def _resolve_dadu(query_or_none, context, session, chat_id):
    result = play_dadu(session.players)
    await _distribute_rewards(context, session, result, chat_id)

    msg = result["description"] + "\n\n" + _reward_summary(session, result)
    if query_or_none:
        await query_or_none.edit_message_text(msg, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, msg, parse_mode="Markdown")
    sess.delete_session(chat_id)


async def handle_game_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data  # game_choice_xxx or game_open_xxx_yyy

    session = sess.get_session(chat_id)

    # Handle game menu open
    if data.startswith("game_open_"):
        parts = data.split("_")
        game_type = parts[2]
        bet = int(parts[3]) if len(parts) > 3 else DEFAULT_BET
        db.get_user(user.id, user.username or user.first_name)
        # Buat message baru sebagai update message
        await query.edit_message_text(
            f"🎰 Membuka game *{GAME_INFO.get(game_type, {}).get('name', game_type)}*...",
            parse_mode="Markdown"
        )
        # Buka game
        if sess.has_active_game(chat_id):
            await query.edit_message_text("⚠️ Sudah ada game aktif!")
            return
        data_user = db.get_user(user.id)
        if data_user["coins"] < bet:
            await query.edit_message_text(
                f"❌ Saldo tidak cukup! Butuh {bet:,} 🪙, punya {data_user['coins']:,} 🪙"
            )
            return
        session = sess.create_session(chat_id, game_type, user.id, bet)
        session.add_player(user.id, user.username or user.first_name)
        session.message_id = query.message.message_id
        await query.edit_message_text(
            _lobby_text(session),
            parse_mode="Markdown",
            reply_markup=_game_keyboard(game_type, "waiting")
        )
        return

    if data == "game_help":
        lines = ["📖 *Panduan Game:*\n"]
        for key, info in GAME_INFO.items():
            lines.append(f"*{info['name']}*: {info['desc']}")
        lines.append("\nBuka game: `/game [mode] [bet]`")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return

    # Handle pilihan pemain
    if data.startswith("game_choice_") and session and session.phase == "playing":
        if not session.has_player(user.id):
            await query.answer("Kamu tidak dalam game ini!", show_alert=True)
            return

        choice = data.replace("game_choice_", "")
        choices_so_far = session.game_data.get("choices", {})

        if user.id in choices_so_far:
            await query.answer("Sudah pilih! Tunggu pemain lain.", show_alert=True)
            return

        choices_so_far[user.id] = choice
        session.game_data["choices"] = choices_so_far
        await query.answer(f"✅ Kamu pilih: {choice.upper()}")

        # Cek apakah semua sudah pilih
        if len(choices_so_far) >= session.player_count():
            await _resolve_choice_game(query, context, session, chat_id)


async def _resolve_choice_game(query, context, session, chat_id):
    choices = session.game_data.get("choices", {})
    game_type = session.game_type

    if game_type == "coinflip":
        result = play_coinflip(session.players, choices)
    elif game_type == "tebak_angka":
        result = play_tebak_angka(session.players, choices)
    elif game_type == "roulette":
        result = play_roulette(session.players, choices)
    else:
        result = {"winner_ids": [], "loser_ids": list(session.players.keys()),
                  "description": "❌ Mode tidak dikenali."}

    await _distribute_rewards(context, session, result, chat_id)
    summary = _reward_summary(session, result)
    full_msg = result["description"] + "\n\n" + summary

    await query.edit_message_text(full_msg, parse_mode="Markdown")
    sess.delete_session(chat_id)


async def _distribute_rewards(context, session, result, chat_id):
    is_draw = result.get("is_draw", False)
    bet = session.bet
    multiplier = result.get("multiplier", 2)

    if is_draw:
        # Refund semua
        for uid in session.players:
            db.update_coins(uid, bet)
        return

    winner_ids = result.get("winner_ids", [])
    loser_ids = result.get("loser_ids", [])
    total_losers = len(loser_ids)
    total_winners = len(winner_ids)

    if not winner_ids:
        return

    for uid in winner_ids:
        # Kembalikan bet + profit
        if total_winners == 1 and total_losers > 0:
            # Winner ambil semua pot
            profit = total_losers * bet
            db.update_coins(uid, bet + profit)
            db.record_win(uid, profit)
        else:
            # Multiple winners: bayar multiplier
            winnings = int(bet * multiplier)
            db.update_coins(uid, winnings)
            db.record_win(uid, winnings - bet)

    for uid in loser_ids:
        db.record_loss(uid, bet)


def _reward_summary(session, result) -> str:
    is_draw = result.get("is_draw", False)
    bet = session.bet
    multiplier = result.get("multiplier", 2)
    winner_ids = result.get("winner_ids", [])
    loser_ids = result.get("loser_ids", [])

    if is_draw:
        return "🤝 *Seri! Semua koin dikembalikan.*"

    lines = ["💰 *Hasil:*"]
    if winner_ids:
        if len(winner_ids) == 1 and loser_ids:
            profit = len(loser_ids) * bet
            total = bet + profit
            wname = session.players.get(winner_ids[0], "?")
            lines.append(f"🏆 {wname}: +{profit:,} 🪙 (total: {total:,})")
        else:
            winnings = int(bet * multiplier)
            for uid in winner_ids:
                name = session.players.get(uid, "?")
                lines.append(f"🏆 {name}: +{winnings - bet:,} 🪙 (dapat {winnings:,})")

    for uid in loser_ids:
        name = session.players.get(uid, "?")
        lines.append(f"💀 {name}: -{bet:,} 🪙")

    return "\n".join(lines)
