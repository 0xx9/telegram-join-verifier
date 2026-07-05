import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ChatJoinRequestHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

FORWARD_TO = 8220091004

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_user(user_id: int, first_name: str, username: str | None, chat_title: str):
    users = load_users()
    users[str(user_id)] = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "chat_title": chat_title,
        "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-approve join request and send welcome message."""
    join_request = update.chat_join_request
    user = join_request.from_user
    chat = join_request.chat

    # Approve immediately
    try:
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        save_user(user.id, user.first_name, user.username, chat.title or "القناة")
        logger.info(f"Approved user {user.id} ({user.full_name}) into {chat.title}")
    except Exception as e:
        logger.error(f"Failed to approve user {user.id}: {e}")
        return

    # Send welcome message
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"أهلاً بك {user.first_name}\n\n"
                f"تمت الموافقة على طلبك والانضمام إلى {chat.title}"
            ),
        )
    except Exception as e:
        logger.warning(f"Could not DM user {user.id}: {e}")




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً! أنا بوت التحقق من طلبات الانضمام.\n"
        "أضفني كمشرف في قناتك الخاصة للبدء."
    )


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_users()
    if not users:
        await update.message.reply_text("لا يوجد مستخدمون محفوظون بعد.")
        return
    lines = [f"👥 عدد المستخدمين: <b>{len(users)}</b>\n"]
    for u in list(users.values())[-20:]:  # آخر 20 فقط
        uname = f"@{u['username']}" if u.get("username") else "—"
        lines.append(f"• <b>{u['first_name']}</b> ({uname}) — <code>{u['id']}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /broadcast الرسالة هنا")
        return
    message = " ".join(context.args)
    users = load_users()
    if not users:
        await update.message.reply_text("لا يوجد مستخدمون محفوظون.")
        return
    sent, failed = 0, 0
    for u in users.values():
        try:
            await context.bot.send_message(chat_id=u["id"], text=message)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"✅ تم الإرسال: <b>{sent}</b>\n❌ فشل: <b>{failed}</b>",
        parse_mode="HTML",
    )


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward any incoming message to the admin."""
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    # Don't forward admin's own messages back to himself
    if user.id == FORWARD_TO:
        return
    try:
        await context.bot.forward_message(
            chat_id=FORWARD_TO,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
    except Exception as e:
        logger.warning(f"Could not forward message from {user.id}: {e}")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set in environment variables!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_admin))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
