import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return

    kb = [[
        InlineKeyboardButton("💰 Beri Koin", callback_data="admin_givecoin"),
        InlineKeyboardButton("🗑️ Reset User", callback_data="admin_reset"),
    ], [
        InlineKeyboardButton("📊 Stats DB", callback_data="admin_stats"),
        InlineKeyboardButton("👥 List Users", callback_data="admin_listusers"),
    ]]

    await update.message.reply_text(
        "⚙️ *Admin Panel*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not is_admin(user.id):
        await query.answer("Bukan admin!", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "admin_stats":
        data = db._load()
        total_users = len(data)
        total_coins = sum(u.get("coins", 0) for u in data.values())
        await query.edit_message_text(
            f"📊 *DB Stats*\n\n"
            f"Total user: {total_users}\n"
            f"Total koin beredar: {total_coins:,} 🪙",
            parse_mode="Markdown"
        )

    elif action == "admin_givecoin":
        await query.edit_message_text(
            "💰 *Beri Koin*\n\nGunakan command:\n`/givecoin @username jumlah`\n\nAtau beri ke semua:\n`/addcoins all jumlah`",
            parse_mode="Markdown"
        )

    elif action == "admin_reset":
        await query.edit_message_text(
            "🗑️ *Reset User*\n\nGunakan command:\n`/resetuser @username`",
            parse_mode="Markdown"
        )

    elif action == "admin_listusers":
        await query.edit_message_text(
            "👥 *List Users*\n\nGunakan command:\n`/listusers`",
            parse_mode="Markdown"
        )


async def givecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /givecoin @username 1000"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Format: `/givecoin @username jumlah`", parse_mode="Markdown")
        return

    target_username = context.args[0].lstrip("@").lower()
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0.")
        return

    data = db._load()
    target = next(
        (u for u in data.values() if u.get("username", "").lower() == target_username),
        None
    )

    if not target:
        await update.message.reply_text(f"❌ User `@{target_username}` tidak ditemukan.", parse_mode="Markdown")
        return

    new_balance = db.update_coins(target["user_id"], amount)
    await update.message.reply_text(
        f"✅ Berhasil memberi *{amount:,} 🪙* ke @{target['username']}\n"
        f"Saldo baru: *{new_balance:,} 🪙*",
        parse_mode="Markdown"
    )


async def resetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /resetuser @username"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❌ Format: `/resetuser @username`", parse_mode="Markdown")
        return

    target_username = context.args[0].lstrip("@").lower()
    data = db._load()
    target = next(
        (u for u in data.values() if u.get("username", "").lower() == target_username),
        None
    )

    if not target:
        await update.message.reply_text(f"❌ User `@{target_username}` tidak ditemukan.", parse_mode="Markdown")
        return

    db.set_coins(target["user_id"], db.STARTING_COINS)
    await update.message.reply_text(
        f"✅ Saldo @{target['username']} di-reset ke *{db.STARTING_COINS:,} 🪙*",
        parse_mode="Markdown"
    )


async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /addcoins all 500"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Format: `/addcoins all jumlah`", parse_mode="Markdown")
        return

    if context.args[0].lower() != "all":
        await update.message.reply_text("❌ Saat ini hanya mendukung `all`. Contoh: `/addcoins all 500`", parse_mode="Markdown")
        return

    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0.")
        return

    data = db._load()
    if not data:
        await update.message.reply_text("❌ Belum ada user terdaftar.")
        return

    for uid in data:
        data[uid]["coins"] = max(0, data[uid].get("coins", 0) + amount)
    db._save(data)

    await update.message.reply_text(
        f"✅ Berhasil memberi *{amount:,} 🪙* ke *{len(data)} user*",
        parse_mode="Markdown"
    )


async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /listusers"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return

    data = db._load()
    if not data:
        await update.message.reply_text("❌ Belum ada user terdaftar.")
        return

    users_sorted = sorted(data.values(), key=lambda x: x.get("coins", 0), reverse=True)

    lines = ["👥 *Daftar User & Saldo*\n"]
    for i, u in enumerate(users_sorted, 1):
        username = u.get("username", f"User{u['user_id']}")
        coins = u.get("coins", 0)
        lines.append(f"{i}. @{username} — {coins:,} 🪙")

    # Telegram message limit ~4096 chars, chunk if needed
    msg = "\n".join(lines)
    if len(msg) > 4000:
        chunks = []
        chunk = ["👥 *Daftar User & Saldo*\n"]
        for line in lines[1:]:
            chunk.append(line)
            if len("\n".join(chunk)) > 3800:
                chunks.append("\n".join(chunk[:-1]))
                chunk = [line]
        chunks.append("\n".join(chunk))
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")
