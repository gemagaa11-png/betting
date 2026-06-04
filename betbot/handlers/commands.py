from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db


HELP_TEXT = """
🎰 *BETBOT — Panduan Lengkap*

━━━━━━━━━━━━━━━
💰 *EKONOMI*
━━━━━━━━━━━━━━━
/saldo — Cek koin kamu
/daily — Ambil reward harian (+200 🪙)
/transfer @user jumlah — Transfer koin
/leaderboard — Top 10 terkaya

━━━━━━━━━━━━━━━
🎮 *GAME GRUP*
━━━━━━━━━━━━━━━
/game [mode] [bet] — Buka sesi game baru
Contoh: `/game coinflip 100`
Mode: `coinflip`, `dadu`, `tebak_angka`, `roulette`

/join — Ikut game yang sedang dibuka
/startgame — Mulai game (host only)
/cancel — Batalkan game (host only)

━━━━━━━━━━━━━━━
⚔️ *PVP (1 vs 1)*
━━━━━━━━━━━━━━━
/duel @lawan [mode] [bet] — Tantang pemain
Contoh: `/duel @budi suit 500`
Mode PvP: `suit`, `coinflip`, `dadu`

━━━━━━━━━━━━━━━
💡 *INFO*
━━━━━━━━━━━━━━━
• Saldo awal: 1,000 🪙
• Daily reward: 200 🪙
• Menang = bet x2 (kecuali roulette hijau = 5x)
• Kalah = kehilangan bet
• Saldo min 0 🪙 (tidak bisa minus)
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username or user.first_name)

    kb = [[
        InlineKeyboardButton("💰 Saldo", callback_data="cmd_balance"),
        InlineKeyboardButton("🎁 Daily", callback_data="cmd_daily"),
    ], [
        InlineKeyboardButton("📖 Panduan", callback_data="cmd_help"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="cmd_leaderboard"),
    ]]

    text = (
        f"🎰 *Selamat datang di BetBot, {user.first_name}!*\n\n"
        "Virtual betting game untuk grup Telegram.\n"
        "Semua menggunakan koin virtual — bebas risiko! 😄\n\n"
        "Kamu mendapat *1,000 🪙* koin awal.\n"
        "Gunakan /help untuk panduan lengkap."
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username or user.first_name)
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = db.get_user(user.id, user.username or user.first_name)
    total = data["wins"] + data["losses"]
    wr = f"{data['wins']/total*100:.0f}%" if total > 0 else "N/A"

    text = (
        f"💰 *Saldo: {data['coins']:,} 🪙*\n\n"
        f"👤 {data['username']}\n"
        f"🏆 Menang: {data['wins']} | 💀 Kalah: {data['losses']}\n"
        f"📊 Win Rate: {wr}\n"
        f"📈 Total menang: {data['total_won']:,} 🪙\n"
        f"📉 Total kalah: {data['total_lost']:,} 🪙"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username or user.first_name)
    success, coins, remaining = db.claim_daily(user.id)

    if success:
        data = db.get_user(user.id)
        await update.message.reply_text(
            f"🎁 *Daily reward diklaim!*\n\n"
            f"+{coins:,} 🪙\n"
            f"Saldo sekarang: *{data['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
    else:
        hours = remaining // 3600
        mins = (remaining % 3600) // 60
        await update.message.reply_text(
            f"⏳ Sudah klaim hari ini!\n"
            f"Bisa ambil lagi dalam *{hours}j {mins}m*",
            parse_mode="Markdown"
        )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = db.get_leaderboard(10)
    lines = ["🏆 *TOP 10 TERKAYA*\n"]
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, u in enumerate(top):
        lines.append(f"{medals[i]} {u['username']} — {u['coins']:,} 🪙")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username or user.first_name)
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "📤 *Format:* `/transfer @username jumlah`\n"
            "Contoh: `/transfer @budi 500`",
            parse_mode="Markdown"
        )
        return

    target_mention = args[0].lstrip("@")
    try:
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus angka.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0.")
        return

    sender = db.get_user(user.id)
    if sender["coins"] < amount:
        await update.message.reply_text(
            f"❌ Koin tidak cukup. Saldo: *{sender['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
        return

    # Simpan pending transfer di context
    context.user_data["pending_transfer"] = {
        "target_username": target_mention,
        "amount": amount
    }

    # Cari user di DB berdasarkan username
    all_users = db._load()
    target_data = None
    for uid, udata in all_users.items():
        if udata.get("username", "").lower() == target_mention.lower():
            target_data = udata
            break

    if not target_data:
        await update.message.reply_text(
            f"❌ User @{target_mention} tidak ditemukan.\n"
            "Pastikan mereka sudah pernah pakai /start di bot ini."
        )
        return

    context.user_data["pending_transfer"]["target_id"] = target_data["user_id"]
    context.user_data["pending_transfer"]["target_display"] = target_data["username"]

    kb = [[
        InlineKeyboardButton("✅ Konfirmasi", callback_data=f"transfer_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="transfer_cancel"),
    ]]
    await update.message.reply_text(
        f"📤 *Konfirmasi Transfer*\n\n"
        f"Kepada: @{target_data['username']}\n"
        f"Jumlah: *{amount:,} 🪙*\n\n"
        f"Saldo setelahnya: *{sender['coins'] - amount:,} 🪙*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def transfer_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "transfer_cancel":
        context.user_data.pop("pending_transfer", None)
        await query.edit_message_text("❌ Transfer dibatalkan.")
        return

    pending = context.user_data.get("pending_transfer")
    if not pending:
        await query.edit_message_text("❌ Tidak ada transfer yang tertunda.")
        return

    ok, msg = db.transfer_coins(user.id, pending["target_id"], pending["amount"])
    context.user_data.pop("pending_transfer", None)

    if ok:
        sender = db.get_user(user.id)
        await query.edit_message_text(
            f"✅ *Transfer berhasil!*\n\n"
            f"Dikirim ke: @{pending['target_display']}\n"
            f"Jumlah: *{pending['amount']:,} 🪙*\n"
            f"Saldo kamu: *{sender['coins']:,} 🪙*",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(f"❌ Gagal: {msg}")
