import os
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from handlers.commands import (
    start, help_cmd, balance, daily, leaderboard,
    transfer, transfer_confirm
)
from handlers.game_handler import (
    game_menu, join_game, leave_game, start_round,
    handle_game_action, cancel_game
)
from handlers.pvp_handler import (
    pvp_challenge, pvp_accept, pvp_decline, handle_pvp_action
)
from handlers.admin_handler import (
    admin_panel, admin_action,
    givecoin, resetuser, addcoins, listusers
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable tidak ditemukan!")

    app = Application.builder().token(token).build()

    # === BASIC COMMANDS ===
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("saldo", balance))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("transfer", transfer))

    # === GAME COMMANDS ===
    app.add_handler(CommandHandler("game", game_menu))
    app.add_handler(CommandHandler("join", join_game))
    app.add_handler(CommandHandler("leave", leave_game))
    app.add_handler(CommandHandler("startgame", start_round))
    app.add_handler(CommandHandler("cancel", cancel_game))

    # === PVP COMMANDS ===
    app.add_handler(CommandHandler("duel", pvp_challenge))
    app.add_handler(CommandHandler("bet", pvp_challenge))

    # === ADMIN COMMANDS ===
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("givecoin", givecoin))
    app.add_handler(CommandHandler("resetuser", resetuser))
    app.add_handler(CommandHandler("addcoins", addcoins))
    app.add_handler(CommandHandler("listusers", listusers))

    # === CALLBACK QUERY HANDLERS ===
    app.add_handler(CallbackQueryHandler(join_game, pattern="^join_game$"))
    app.add_handler(CallbackQueryHandler(leave_game, pattern="^leave_game$"))
    app.add_handler(CallbackQueryHandler(start_round, pattern="^start_round$"))
    app.add_handler(CallbackQueryHandler(cancel_game, pattern="^cancel_game$"))
    app.add_handler(CallbackQueryHandler(handle_game_action, pattern="^game_"))
    app.add_handler(CallbackQueryHandler(pvp_accept, pattern="^pvp_accept_"))
    app.add_handler(CallbackQueryHandler(pvp_decline, pattern="^pvp_decline_"))
    app.add_handler(CallbackQueryHandler(handle_pvp_action, pattern="^pvp_"))
    app.add_handler(CallbackQueryHandler(transfer_confirm, pattern="^transfer_"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^admin_"))

    logger.info("🎰 BetBot starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
