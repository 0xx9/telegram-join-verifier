"""
send_pending.py — يرسل رسالة التحقق للمستخدمين الذين قدّموا طلبات انضمام قديمة
يعمل مرة واحدة فقط، ثم يوقف نفسه.
"""

import asyncio
import json
import os
import httpx
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid

load_dotenv()

API_ID      = int(os.getenv("PYROGRAM_API_ID", "0"))
API_HASH    = os.getenv("PYROGRAM_API_HASH", "")
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
CHANNEL_ID  = os.getenv("CHANNEL_ID", "")   # مثال: @mychannel أو -100xxxxxxxxx
DELAY       = float(os.getenv("PENDING_DELAY", "1.5"))  # ثواني بين كل رسالة

SENT_FILE = "sent_pending.json"


def load_sent() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_sent(sent: set):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)


async def send_verification_message(user_id: int, first_name: str, channel_title: str, channel_id: int) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [[{
            "text": "✅ أنا لست روبوت",
            "callback_data": f"verify_{user_id}_{channel_id}"
        }]]
    }
    payload = {
        "chat_id": user_id,
        "text": (
            f"أهلاً بك {first_name} 👋\n\n"
            f"قدّمت طلب انضمام إلى <b>{channel_title}</b>\n\n"
            f"الرجاء الضغط على الزر والإثبات أنك لست روبوت."
        ),
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            return r.status_code == 200
    except Exception:
        return False


async def main():
    if not API_ID or not API_HASH:
        print("❌ PYROGRAM_API_ID و PYROGRAM_API_HASH غير موجودين في .env")
        return
    if not CHANNEL_ID:
        print("❌ CHANNEL_ID غير موجود في .env")
        return

    sent = load_sent()

    async with Client("session_pending", api_id=API_ID, api_hash=API_HASH) as app:
        # Preload dialogs so Pyrogram knows about the channel
        print("⏳ جاري تحميل المحادثات لتعريف القناة...")
        channel = None
        target_id = int(CHANNEL_ID) if str(CHANNEL_ID).lstrip("-").isdigit() else None
        async for dialog in app.get_dialogs():
            cid = dialog.chat.id
            if cid == target_id or str(cid) == CHANNEL_ID or f"-100{cid}" == CHANNEL_ID:
                channel = dialog.chat
                break
        if channel is None:
            try:
                channel = await app.get_chat(CHANNEL_ID)
            except Exception as e:
                print(f"❌ تعذّر الوصول للقناة: {e}")
                print("تأكد أن حسابك عضو أو مشرف في القناة.")
                return

        channel_title = channel.title or "القناة"
        channel_numeric_id = channel.id
        print(f"📢 القناة: {channel_title} ({channel_numeric_id})")
        print(f"⏳ جاري جلب الطلبات المعلقة...\n")

        total = 0
        sent_count = 0
        skipped = 0
        failed = 0

        async for request in app.get_chat_join_requests(CHANNEL_ID):
            user = request.user
            user_id = user.id
            total += 1

            if str(user_id) in sent:
                skipped += 1
                print(f"⏭️  تخطي: {user.first_name} ({user_id}) — تم الإرسال مسبقاً")
                continue

            try:
                success = await send_verification_message(
                    user_id, user.first_name, channel_title, channel_numeric_id
                )
                if success:
                    sent.add(str(user_id))
                    save_sent(sent)
                    sent_count += 1
                    print(f"✅ أُرسل إلى: {user.first_name} ({user_id})")
                else:
                    failed += 1
                    print(f"❌ فشل الإرسال: {user.first_name} ({user_id})")

            except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
                failed += 1
                print(f"🚫 لا يمكن مراسلة: {user.first_name} ({user_id})")
            except FloodWait as e:
                print(f"⚠️  انتظار {e.value} ثانية بسبب flood wait...")
                await asyncio.sleep(e.value)
                continue


    print(f"\n{'='*40}")
    print(f"📊 الإجمالي: {total} طلب")
    print(f"✅ تم الإرسال: {sent_count}")
    print(f"⏭️  تخطي (مرسل مسبقاً): {skipped}")
    print(f"❌ فشل: {failed}")
    print(f"{'='*40}")


if __name__ == "__main__":
    asyncio.run(main())
