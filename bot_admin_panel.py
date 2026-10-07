import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# =========================================================
# SETTINGS
# =========================================================
BOT_TOKEN = "8597443240:AAHT_Sjw68kw4ly4wenzhkEGarD5IBK9u9U"
ADMIN_ID = 8095865032

DB_NAME = "bot_database.db"

# =========================================================
# DATABASE
# =========================================================
def db_connect():
    return sqlite3.connect(DB_NAME)

def create_database():
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        tokens INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        duration INTEGER,
        key_text TEXT,
        used INTEGER DEFAULT 0,
        used_by INTEGER DEFAULT NULL,
        used_at TEXT DEFAULT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        duration INTEGER,
        key_text TEXT,
        created_at TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        name TEXT PRIMARY KEY,
        value TEXT
    )""")

    defaults = {
        "main_channel": "@mrarman805",
        "update_channel": "@rxarman05",
        "get_key_bot": "https://t.me/SiamShop2026_bot",
        "price_6": "150",
        "price_12": "290",
        "price_24": "350",
        "reward": "20",
        "bot_name": "Gtools Bot",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(name,value) VALUES(?,?)", (k, v))

    conn.commit()
    conn.close()

def get_setting(name, default=""):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE name=?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(name, value):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings(name,value) VALUES(?,?) "
        "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
        (name, str(value))
    )
    conn.commit()
    conn.close()

def create_user(user):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users(user_id,username,first_name) VALUES(?,?,?)",
            (user.id, user.username or "", user.first_name or "")
        )
    else:
        cur.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (user.username or "", user.first_name or "", user.id)
        )
    conn.commit()
    conn.close()

# =========================================================
# PUBLIC MENUS
# =========================================================
def join_keyboard():
    main = get_setting("main_channel", "@mrarman805")
    update = get_setting("update_channel", "@rxarman05")
    getbot = get_setting("get_key_bot", "https://t.me/SiamShop2026_bot")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Main Channel",
                              url="https://t.me/" + main.lstrip("@"))],
        [InlineKeyboardButton("📢 Join Update Channel",
                              url="https://t.me/" + update.lstrip("@"))],
        [InlineKeyboardButton("🤖 Join Get Key Bot", url=getbot)],
        [InlineKeyboardButton("✅ Joined / Verified", callback_data="verify")]
    ])

def main_menu():
    getbot = get_setting("get_key_bot", "https://t.me/SiamShop2026_bot")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profile", callback_data="profile"),
         InlineKeyboardButton("🔗 Refer", callback_data="refer")],
        [InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem"),
         InlineKeyboardButton("🔑 Get Key", callback_data="getkey")],
        [InlineKeyboardButton("🛒 Shop Now", url=getbot),
         InlineKeyboardButton("🔑 My Keys", callback_data="mykeys")]
    ])

# =========================================================
# START / VERIFY
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user)

    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                conn = db_connect()
                cur = conn.cursor()
                cur.execute("SELECT referred_by FROM users WHERE user_id=?", (user.id,))
                result = cur.fetchone()
                if result and result[0] is None:
                    cur.execute("UPDATE users SET referred_by=? WHERE user_id=?",
                                (referrer_id, user.id))
                    conn.commit()
                conn.close()
        except ValueError:
            pass

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT verified FROM users WHERE user_id=?", (user.id,))
    result = cur.fetchone()
    conn.close()

    if result and result[0] == 1:
        await update.message.reply_text(
            f"🤖 {get_setting('bot_name','Gtools Bot')} Activated!\n\n"
            "👋 Welcome back.\n\nUse the menu below to navigate.",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "⚠️ Please join all required channels first.",
            reply_markup=join_keyboard()
        )

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    not_joined = []

    for setting_name, label in [
        ("main_channel", "Main Channel"),
        ("update_channel", "Update Channel")
    ]:
        channel = get_setting(setting_name)
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(label)
        except Exception:
            not_joined.append(label)

    if not_joined:
        await query.edit_message_text(
            "❌ Verification Failed!\n\nNot joined:\n" +
            "\n".join("❌ " + x for x in not_joined) +
            "\n\nJoin them and press Verify again.",
            reply_markup=join_keyboard()
        )
        return

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT verified,referred_by FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    already_verified = result[0] if result else 0
    referred_by = result[1] if result else None

    cur.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
    if not already_verified and referred_by:
        reward = int(get_setting("reward", "20"))
        cur.execute(
            "UPDATE users SET tokens=tokens+?, referrals=referrals+1 WHERE user_id=?",
            (reward, referred_by)
        )
    conn.commit()
    conn.close()

    await query.edit_message_text(
        "🎉 Verification Successful!\n\n"
        f"🤖 {get_setting('bot_name','Gtools Bot')} Activated!",
        reply_markup=main_menu()
    )

# =========================================================
# USER FEATURES
# =========================================================
async def profile(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT first_name,username,tokens,referrals FROM users WHERE user_id=?",
                (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return
    first_name, username, tokens, referrals = row
    await query.edit_message_text(
        f"👤 Your Profile\n\n"
        f"👤 Name: {first_name}\n🆔 ID: {user_id}\n"
        f"👥 Referrals: {referrals}\n🪙 Tokens: {tokens}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        )
    )

async def refer(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT referrals,tokens FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    referrals, tokens = row if row else (0, 0)
    await query.edit_message_text(
        f"🔗 Your Referral Link\n\n{link}\n\n"
        f"👥 Total Referrals: {referrals}\n"
        f"🎁 Reward: {get_setting('reward','20')} tokens\n"
        f"🪙 Your Tokens: {tokens}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Referral Link",
                                  url=f"https://t.me/share/url?url={link}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )

async def get_key(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 Get Key\n\nChoose a key duration:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"🔑 6 Hours — {get_setting('price_6','150')} Tokens",
                callback_data="key_6")],
            [InlineKeyboardButton(
                f"🔑 12 Hours — {get_setting('price_12','290')} Tokens",
                callback_data="key_12")],
            [InlineKeyboardButton(
                f"🔑 24 Hours — {get_setting('price_24','350')} Tokens",
                callback_data="key_24")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )

async def redeem_key(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    duration = int(query.data.replace("key_", ""))
    prices = {
        6: int(get_setting("price_6","150")),
        12: int(get_setting("price_12","290")),
        24: int(get_setting("price_24","350"))
    }
    cost = prices.get(duration, 0)

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT tokens FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        await query.edit_message_text("❌ User not found.")
        return

    tokens = row[0]
    if tokens < cost:
        conn.close()
        await query.edit_message_text(
            f"❌ Not enough tokens!\n\n🪙 Your Tokens: {tokens}\n"
            f"🪙 Required: {cost}\n❗ Need: {cost-tokens} more.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Refer Friends", callback_data="refer")],
                [InlineKeyboardButton("🔙 Back", callback_data="getkey")]
            ])
        )
        return

    cur.execute(
        "SELECT id,key_text FROM keys WHERE duration=? AND used=0 LIMIT 1",
        (duration,)
    )
    key_row = cur.fetchone()
    if not key_row:
        conn.close()
        await query.edit_message_text(
            f"⚠️ No {duration}-hour key is available right now.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="getkey")]]
            )
        )
        return

    key_id, key_text = key_row
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE users SET tokens=tokens-? WHERE user_id=?", (cost, user_id))
    cur.execute(
        "UPDATE keys SET used=1,used_by=?,used_at=? WHERE id=?",
        (user_id, now, key_id)
    )
    cur.execute(
        "INSERT INTO user_keys(user_id,duration,key_text,created_at) VALUES(?,?,?,?)",
        (user_id, duration, key_text, now)
    )
    conn.commit()
    conn.close()

    await query.edit_message_text(
        f"🎉 Key Redeemed Successfully!\n\n⏱ Duration: {duration} Hours\n"
        f"🔑 Key:\n`{key_text}`\n\n🪙 Tokens Used: {cost}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 My Keys", callback_data="mykeys")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )

async def my_keys(update, context):
    query = update.callback_query
    await query.answer()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT duration,key_text,created_at FROM user_keys "
        "WHERE user_id=? ORDER BY id DESC LIMIT 10", (query.from_user.id,)
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        text = "🔑 My Keys\n\nYou have not redeemed any keys yet."
    else:
        text = "🔑 My Keys\n\n" + "".join(
            f"⏱ {d} Hours\n🔑 `{k}`\n📅 {t}\n\n" for d,k,t in rows
        )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        )
    )

async def redeem_code(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎟️ Redeem Code\n\nRedeem Code system can be added to the admin panel later.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        )
    )

async def back(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"🤖 {get_setting('bot_name','Gtools Bot')} Activated!",
        reply_markup=main_menu()
    )

# =========================================================
# ADMIN PANEL
# =========================================================
def is_admin(user_id):
    return user_id == ADMIN_ID

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Key Management", callback_data="adm_keys"),
         InlineKeyboardButton("📦 Stock", callback_data="adm_stock")],
        [InlineKeyboardButton("💰 Prices", callback_data="adm_prices"),
         InlineKeyboardButton("👥 Users", callback_data="adm_users")],
        [InlineKeyboardButton("🪙 Token Management", callback_data="adm_tokens"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="adm_settings"),
         InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")],
        [InlineKeyboardButton("❌ Close", callback_data="adm_close")]
    ])

async def admin_command(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    await update.message.reply_text("🛠️ Admin Panel\n\nChoose an option:",
                                    reply_markup=admin_menu())

async def admin_keys(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔑 Key Management\n\n"
        "Add a key with:\n/addkey 6 YOUR_KEY\n"
        "/addkey 12 YOUR_KEY\n"
        "/addkey 24 YOUR_KEY\n\n"
        "Use the buttons below for stock/cleanup.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 View Stock", callback_data="adm_stock")],
            [InlineKeyboardButton("🗑️ Delete Used Keys", callback_data="adm_delete_used")],
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

async def admin_stock(update, context):
    q = update.callback_query
    await q.answer()
    conn = db_connect()
    cur = conn.cursor()
    counts = {}
    used = {}
    for d in [6,12,24]:
        cur.execute("SELECT COUNT(*) FROM keys WHERE duration=? AND used=0", (d,))
        counts[d] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM keys WHERE duration=? AND used=1", (d,))
        used[d] = cur.fetchone()[0]
    conn.close()
    await q.edit_message_text(
        "📦 Key Stock\n\n"
        f"⏱ 6 Hours: {counts[6]} available / {used[6]} used\n"
        f"⏱ 12 Hours: {counts[12]} available / {used[12]} used\n"
        f"⏱ 24 Hours: {counts[24]} available / {used[24]} used",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]]
        )
    )

async def admin_prices(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "💰 Current Prices\n\n"
        f"6 Hours = {get_setting('price_6','150')} tokens\n"
        f"12 Hours = {get_setting('price_12','290')} tokens\n"
        f"24 Hours = {get_setting('price_24','350')} tokens\n\n"
        "Change with commands:\n"
        "/setprice 6 150\n/setprice 12 290\n/setprice 24 350",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]]
        )
    )

async def admin_users(update, context):
    q = update.callback_query
    await q.answer()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE verified=1")
    verified = cur.fetchone()[0]
    conn.close()
    await q.edit_message_text(
        f"👥 Users\n\nTotal Users: {total}\nVerified Users: {verified}\n\n"
        "User token changes:\n/settoken USER_ID AMOUNT",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

async def admin_tokens(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🪙 Token Management\n\n"
        "Add/subtract tokens:\n"
        "/settoken USER_ID AMOUNT\n\n"
        "Example:\n/settoken 123456789 100\n\n"
        "Referral reward:\n"
        f"Current = {get_setting('reward','20')} tokens\n"
        "/setreward 20",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

async def admin_settings(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "⚙️ Settings\n\n"
        f"Bot Name: {get_setting('bot_name','Gtools Bot')}\n"
        f"Main Channel: {get_setting('main_channel')}\n"
        f"Update Channel: {get_setting('update_channel')}\n"
        f"Get Key Bot: {get_setting('get_key_bot')}\n\n"
        "Commands:\n"
        "/setname NAME\n"
        "/setmain @channel\n"
        "/setupdate @channel\n"
        "/setgetbot https://t.me/...\n"
        "/setreward NUMBER",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

async def admin_stats(update, context):
    q = update.callback_query
    await q.answer()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(tokens),0) FROM users")
    tokens = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM user_keys")
    redeemed = cur.fetchone()[0]
    conn.close()
    await q.edit_message_text(
        f"📊 Statistics\n\n👥 Users: {users}\n"
        f"🪙 Total Tokens: {tokens}\n🔑 Redeemed Keys: {redeemed}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

async def admin_close(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("✅ Admin Panel closed.")

async def delete_used_keys(update, context):
    q = update.callback_query
    await q.answer()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM keys WHERE used=1")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    await q.edit_message_text(
        f"🗑️ Deleted {deleted} used key(s).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]
        ])
    )

# =========================================================
# ADMIN COMMANDS
# =========================================================
async def add_key(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n/addkey 6 YOUR_KEY\n/addkey 12 YOUR_KEY\n/addkey 24 YOUR_KEY"
        )
        return
    try:
        duration = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Duration must be 6, 12 or 24.")
        return
    if duration not in [6,12,24]:
        await update.message.reply_text("❌ Duration must be 6, 12 or 24.")
        return
    key_text = " ".join(context.args[1:])
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO keys(duration,key_text) VALUES(?,?)",
                (duration, key_text))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ {duration}-hour key added successfully.")

async def stock_command(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    conn = db_connect()
    cur = conn.cursor()
    vals = []
    for d in [6,12,24]:
        cur.execute("SELECT COUNT(*) FROM keys WHERE duration=? AND used=0", (d,))
        vals.append(cur.fetchone()[0])
    conn.close()
    await update.message.reply_text(
        f"📦 Key Stock\n\n⏱ 6 Hours: {vals[0]}\n"
        f"⏱ 12 Hours: {vals[1]}\n⏱ 24 Hours: {vals[2]}"
    )

async def setprice(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2 or int(context.args[0]) not in [6,12,24]:
        await update.message.reply_text("Usage: /setprice 6 150")
        return
    d, price = context.args
    set_setting(f"price_{d}", price)
    await update.message.reply_text(f"✅ {d}-hour price set to {price} tokens.")

async def settoken(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /settoken USER_ID AMOUNT")
        return
    try:
        uid, amount = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ USER_ID and AMOUNT must be numbers.")
        return
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET tokens=? WHERE user_id=?", (amount, uid))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    await update.message.reply_text(
        "✅ Token balance updated." if changed else "❌ User not found."
    )

async def setreward(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setreward 20")
        return
    try:
        reward = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Reward must be a number.")
        return
    set_setting("reward", reward)
    await update.message.reply_text(f"✅ Referral reward = {reward} tokens.")

async def setname(update, context):
    if not is_admin(update.effective_user.id):
        return
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Usage: /setname Gtools Bot")
        return
    set_setting("bot_name", name)
    await update.message.reply_text("✅ Bot name updated.")

async def setmain(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setmain @channel")
        return
    set_setting("main_channel", context.args[0])
    await update.message.reply_text("✅ Main channel updated.")

async def setupdate(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setupdate @channel")
        return
    set_setting("update_channel", context.args[0])
    await update.message.reply_text("✅ Update channel updated.")

async def setgetbot(update, context):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setgetbot https://t.me/...")
        return
    set_setting("get_key_bot", context.args[0])
    await update.message.reply_text("✅ Get Key Bot link updated.")

async def broadcast(update, context):
    if not is_admin(update.effective_user.id):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /broadcast Your message")
        return

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    user_ids = [r[0] for r in cur.fetchall()]
    conn.close()

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"📢 Broadcast finished.\n\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )

# =========================================================
# BUTTON HANDLER
# =========================================================
async def button_handler(update, context):
    q = update.callback_query
    data = q.data

    if data.startswith("adm_") and not is_admin(q.from_user.id):
        await q.answer("❌ Not authorized.", show_alert=True)
        return

    if data == "verify": await verify_user(update, context)
    elif data == "profile": await profile(update, context)
    elif data == "refer": await refer(update, context)
    elif data == "getkey": await get_key(update, context)
    elif data == "mykeys": await my_keys(update, context)
    elif data == "redeem": await redeem_code(update, context)
    elif data == "back": await back(update, context)
    elif data.startswith("key_"): await redeem_key(update, context)

    elif data == "adm_home":
        await q.answer()
        await q.edit_message_text("🛠️ Admin Panel", reply_markup=admin_menu())
    elif data == "adm_keys": await admin_keys(update, context)
    elif data == "adm_stock": await admin_stock(update, context)
    elif data == "adm_prices": await admin_prices(update, context)
    elif data == "adm_users": await admin_users(update, context)
    elif data == "adm_tokens": await admin_tokens(update, context)
    elif data == "adm_settings": await admin_settings(update, context)
    elif data == "adm_stats": await admin_stats(update, context)
    elif data == "adm_delete_used": await delete_used_keys(update, context)
    elif data == "adm_broadcast":
        await q.answer()
        await q.edit_message_text(
            "📢 Broadcast\n\nUse:\n/broadcast Your message",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Admin Menu", callback_data="adm_home")]]
            )
        )
    elif data == "adm_close": await admin_close(update, context)

# =========================================================
# RUN
# =========================================================
def main():
    create_database()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CommandHandler("setprice", setprice))
    app.add_handler(CommandHandler("settoken", settoken))
    app.add_handler(CommandHandler("setreward", setreward))
    app.add_handler(CommandHandler("setname", setname))
    app.add_handler(CommandHandler("setmain", setmain))
    app.add_handler(CommandHandler("setupdate", setupdate))
    app.add_handler(CommandHandler("setgetbot", setgetbot))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("==============================")
    print("🤖 Bot is running...")
    print("==============================")
    app.run_polling()

if __name__ == "__main__":
    main()
