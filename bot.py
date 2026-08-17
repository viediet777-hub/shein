import asyncio
import logging
import re
import sqlite3
import warnings
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Python 3.13+ me ye harmless warning aati hai, isliye chhupa rahe hain
warnings.filterwarnings("ignore", message="If 'per_message=False'")

# ========================= CONFIG =========================
# BotFather se token yahan daalo
BOT_TOKEN = "8697982898:AAEWN5d9qpfg2sbrgrHM6QMNzIjXvg4HbKU"

# Apna Telegram ID yahan daalo (multiple admins chahiye to comma lagao)
# ID nikalne ke liye Telegram me @getmyid_bot se /start karo
ADMIN_IDS = [8139558808]

# Har kitne referrals par 1 link milega
REFS_PER_LINK = 3
# ==========================================================

SEP = "━━━━━━━━━━━━━━"

# Conversation states
ADD_LINK, DEL_LINK, ADD_CH, DEL_CH, ADD_ADMIN, DEL_ADMIN, BROADCAST_MSG = range(7)

DB_FILE = "spotifyxrefer.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            referred_by INTEGER,
            join_date TEXT,
            referrals INTEGER DEFAULT 0,
            total_refs INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            used_by INTEGER DEFAULT 0,
            used_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            title TEXT,
            username TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            added_at TEXT
        )"""
    )
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    conn = get_db()
    row = conn.execute("SELECT 1 FROM admins WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def stats_text(row, bot_username):
    earned = row["referrals"] // REFS_PER_LINK
    pending = earned - row["claimed"]
    ref_link = f"https://t.me/{bot_username}?start=ref_{row['id']}"
    text = (
        f"📊 *Your Stats*\n"
        f"{SEP}\n"
        f"👥 Referrals: `{row['referrals']}`\n"
        f"🎁 Rewards: `{earned}`\n"
        f"🔓 Claimed: `{row['claimed']}`\n"
        f"⏳ Pending: `{pending}`\n"
        f"{SEP}\n\n"
        f"📢 *Referral Link*\n`{ref_link}`"
    )
    return text, ref_link


def welcome_msg(row, bot_username):
    earned = row["referrals"] // REFS_PER_LINK
    pending = earned - row["claimed"]
    ref_link = f"https://t.me/{bot_username}?start=ref_{row['id']}"
    text = (
        f"🎵 *SpotifyXRefer Bot*\n\n"
        f"1️⃣ Referral link share karo 📤\n"
        f"2️⃣ Har *{REFS_PER_LINK} refer* = 1 Premium 🎁\n"
        f"3️⃣ *Claim* dabao ✅\n\n"
        f"{SEP}\n"
        f"👥 `{row['referrals']}` Refs  •  🎁 `{earned}` Rewards  •  ⏳ `{pending}` Pending\n"
        f"{SEP}\n\n"
        f"📢 Referral Link:\n`{ref_link}`\n\n"
        f"ℹ️ /help • /status"
    )
    return text, ref_link


def ref_buttons(ref_link):
    return InlineKeyboardMarkup(
        [
            [styled("🔗 Referral Link", style="primary", icon=EMOJI_LINK, url=ref_link)],
            [
                styled("🎁 Claim Now", style="success", icon=EMOJI_SUCCESS, callback_data="claim_reward"),
                styled("📊 Stats", style="primary", icon=EMOJI_STATS, callback_data="show_stats"),
            ],
        ]
    )


EMOJI_SUCCESS = "5891063600885273198"
EMOJI_PRIMARY = "5359664288241829619"
EMOJI_PRIMARY2 = "5373141891321699086"
EMOJI_DANGER = "5382224089295365367"
EMOJI_LINK = "5373141891321699086"
EMOJI_STATS = "5359664288241829619"


def styled(text, style=None, icon=None, **kwargs):
    api = {}
    if style:
        api["style"] = style
    if icon:
        api["icon_custom_emoji_id"] = icon
    if api:
        kwargs["api_kwargs"] = api
    return InlineKeyboardButton(text, **kwargs)


def claim_btn():
    return styled(
        "🎁 Claim Now", style="success", icon=EMOJI_SUCCESS, callback_data="claim_reward"
    )


async def check_force_join(bot, user_id):
    conn = get_db()
    channels = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing


def join_buttons(channels):
    kb = []
    for ch in channels:
        if ch["username"]:
            kb.append(
                [
                    styled(
                        f"📢 Join - {ch['title']}",
                        style="primary",
                        icon=EMOJI_PRIMARY,
                        url=f"https://t.me/{ch['username']}",
                    )
                ]
            )
        else:
            kb.append(
                [
                    styled(
                        f"📢 Join - {ch['title']}",
                        style="primary",
                        icon=EMOJI_PRIMARY,
                        url=f"https://t.me/c/{str(ch['chat_id'])[4:]}",
                    )
                ]
            )
    kb.append(
        [
            styled(
                "✅ Verify Karo",
                style="success",
                icon=EMOJI_SUCCESS,
                callback_data="check_join",
            )
        ]
    )
    return InlineKeyboardMarkup(kb)


# --------------------- USER HANDLERS ---------------------

async def start(update, context):
    user = update.effective_user
    args = context.args
    bot = context.bot
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user.id,)).fetchone()

    if row is None:
        referred_by = None
        if args and args[0].startswith("ref_"):
            try:
                rid = int(args[0].split("_")[1])
            except (ValueError, IndexError):
                rid = None
            if rid and rid != user.id:
                ref_exists = conn.execute("SELECT 1 FROM users WHERE id=?", (rid,)).fetchone()
                if ref_exists:
                    referred_by = rid
        conn.execute(
            "INSERT INTO users (id, username, first_name, referred_by, join_date) VALUES (?,?,?,?,?)",
            (user.id, user.username, user.first_name, referred_by, now()),
        )
        conn.commit()
        if referred_by:
            conn.execute(
                "UPDATE users SET referrals = referrals + 1, total_refs = total_refs + 1 WHERE id=?",
                (referred_by,),
            )
            conn.commit()
            ref_row = conn.execute("SELECT * FROM users WHERE id=?", (referred_by,)).fetchone()
            earned = ref_row["referrals"] // REFS_PER_LINK
            if earned - ref_row["claimed"] > 0:
                await bot.send_message(
                    referred_by,
                    f"🎉 *Naya Referral!* 🎉\n"
                    f"{SEP}\n"
                    f"👥 Total Referrals: `{ref_row['referrals']}`\n"
                    f"🎁 Rewards Ready: `{earned - ref_row['claimed']}`\n"
                    f"{SEP}\n\n"
                    f"👇 Neeche button dabao aur link lo!",
                    reply_markup=InlineKeyboardMarkup([[claim_btn()]]),
                    parse_mode="Markdown",
                )
    else:
        conn.execute(
            "UPDATE users SET username=?, first_name=? WHERE id=?",
            (user.username, user.first_name, user.id),
        )
        conn.commit()

    row = conn.execute("SELECT * FROM users WHERE id=?", (user.id,)).fetchone()
    conn.close()

    text, ref_link = welcome_msg(row, bot.username)
    missing = await check_force_join(bot, user.id)
    if missing:
        await update.message.reply_text(
            "🔒 *Sabse pehle ye channels join karo:*\n"
            f"{SEP}\n"
            "👇 Har channel join karo, phir *Verify* dabao:",
            reply_markup=join_buttons(missing),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        text,
        reply_markup=ref_buttons(ref_link),
        parse_mode="Markdown",
    )


async def do_claim(bot, user, send):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user.id,)).fetchone()
    if row is None:
        conn.close()
        await send("❌ Pehle /start karo! 👇")
        return

    missing = await check_force_join(bot, user.id)
    if missing:
        conn.close()
        await send(
            "🔒 *Reward claim karne ke liye pehle ye channels join karo:*\n"
            f"{SEP}\n"
            "👇 Har channel join karo, phir *Check* dabao:",
            reply_markup=join_buttons(missing),
            parse_mode="Markdown",
        )
        return

    earned = row["referrals"] // REFS_PER_LINK
    pending = earned - row["claimed"]
    if pending <= 0:
        need = REFS_PER_LINK - (row["referrals"] % REFS_PER_LINK)
        conn.close()
        await send(
            f"❌ *Abhi koi reward pending nahi!* 🥺\n"
            f"{SEP}\n"
            f"👥 Referrals: `{row['referrals']}`\n"
            f"🎁 Next reward: aur `{need}` referrals\n"
            f"{SEP}\n\n"
            f"📢 Apna referral link share karo:\n`https://t.me/{bot.username}?start=ref_{user.id}`",
            parse_mode="Markdown",
        )
        return

    link = conn.execute(
        "SELECT * FROM links WHERE used_by = 0 ORDER BY id LIMIT 1"
    ).fetchone()
    if link is None:
        conn.close()
        await send(
            "😔 *Links khatam ho gaye!* ⏳\n"
            "Kuch der baad try karo — Admin naye links add kar rahe hain. 🙏"
        )
        return

    conn.execute(
        "UPDATE links SET used_by=?, used_at=? WHERE id=?",
        (user.id, now(), link["id"]),
    )
    conn.execute("UPDATE users SET claimed = claimed + 1 WHERE id=?", (user.id,))
    conn.commit()
    conn.close()
    await send(
        f"🎁 *Spotify Premium Link!* 🎉\n"
        f"{SEP}\n"
        f"🔗 `{link['url']}`\n"
        f"{SEP}\n\n"
        f"⚠️ Link sirf aapke liye hai — share mat karo!\n"
        f"🙏 Aur friends ko bhejo, aur links kamao! 🔥",
        parse_mode="Markdown",
    )


async def claim(update, context):
    await do_claim(context.bot, update.effective_user, update.message.reply_text)


async def status(update, context):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE id=?", (update.effective_user.id,)
    ).fetchone()
    conn.close()
    if row is None:
        await update.message.reply_text("❌ Pehle /start karo! 👇")
        return
    stats, ref_link = stats_text(row, context.bot.username)
    await update.message.reply_text(stats, reply_markup=ref_buttons(ref_link), parse_mode="Markdown")


async def help_cmd(update, context):
    await update.message.reply_text(
        f"🤖 *SpotifyXRefer Bot - Help*\n"
        f"{SEP}\n"
        f"👋 `/start` - Bot start & stats\n"
        f"📊 `/status` - Apne stats dekho\n"
        f"🎁 `/claim` - Reward claim karo\n"
        f"{SEP}\n\n"
        f"💰 *Kaise kaam karta hai?*\n"
        f"Apna referral link share karo, har *{REFS_PER_LINK} referrals* = *1 Spotify Premium Link* 🎁",
        parse_mode="Markdown",
    )


# --------------------- CALLBACKS ---------------------

async def check_join_cb(update, context):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass
    missing = await check_force_join(context.bot, q.from_user.id)
    if missing:
        await q.message.reply_text(
            "❌ *Abhi bhi kuch channels join nahi kiye!*\n"
            f"{SEP}\n"
            "👇 Channels join karo, phir *Verify* dabao:",
            reply_markup=join_buttons(missing),
            parse_mode="Markdown",
        )
    else:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE id=?", (q.from_user.id,)).fetchone()
        conn.close()
        if row is None:
            await q.message.reply_text("❌ Pehle /start karo! 👇")
            return
        text, ref_link = welcome_msg(row, context.bot.username)
        await q.message.reply_text(
            "✅ *Verify ho gaya!* 🎉\n" f"{SEP}\n\n" + text,
            reply_markup=ref_buttons(ref_link),
            parse_mode="Markdown",
        )


async def claim_cb(update, context):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass
    await do_claim(context.bot, q.from_user, q.message.reply_text)


async def stats_cb(update, context):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (q.from_user.id,)).fetchone()
    conn.close()
    if row is None:
        await q.message.reply_text("❌ Pehle /start karo! 👇")
        return
    stats, ref_link = stats_text(row, context.bot.username)
    await q.message.reply_text(stats, reply_markup=ref_buttons(ref_link), parse_mode="Markdown")


async def error_handler(update, context):
    logger.error("Update %s caused error %s", update, context.error, exc_info=context.error)


# --------------------- ADMIN PANEL ---------------------

PANEL_TEXT = "🛠️ *Admin Panel*\n" f"{SEP}\n" "Sab kuch yahin se control karo 🔥\n" f"{SEP}"


def admin_kb():
    return InlineKeyboardMarkup(
        [
            [
                styled(
                    "➕ Add Links",
                    style="success",
                    icon=EMOJI_SUCCESS,
                    callback_data="admin_addlink",
                ),
                styled(
                    "➖ Remove Link",
                    style="danger",
                    icon=EMOJI_DANGER,
                    callback_data="admin_dellink",
                ),
            ],
            [
                styled(
                    "📊 Links",
                    style="primary",
                    icon=EMOJI_STATS,
                    callback_data="admin_links",
                ),
                styled(
                    "👥 Users",
                    style="primary",
                    icon=EMOJI_PRIMARY,
                    callback_data="admin_users",
                ),
            ],
            [
                styled(
                    "📢 Force Join",
                    style="primary",
                    icon=EMOJI_PRIMARY,
                    callback_data="admin_channels",
                ),
                styled(
                    "👤 Admins",
                    style="primary",
                    icon=EMOJI_PRIMARY2,
                    callback_data="admin_admins",
                ),
            ],
            [
                styled(
                    "📣 Broadcast",
                    style="primary",
                    icon=EMOJI_PRIMARY2,
                    callback_data="admin_broadcast",
                )
            ],
        ]
    )


async def admin_cmd(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ye command sirf admin ke liye hai!")
        return ConversationHandler.END
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    total_links = conn.execute("SELECT COUNT(*) c FROM links").fetchone()["c"]
    used_links = conn.execute("SELECT COUNT(*) c FROM links WHERE used_by != 0").fetchone()["c"]
    conn.close()
    text = (
        "🛠️ *Admin Panel* 🛠️\n"
        f"{SEP}\n"
        f"👤 Users: `{total_users}`  •  🟢 Links Left: `{total_links - used_links}`\n"
        f"{SEP}"
    )
    await update.message.reply_text(text, reply_markup=admin_kb(), parse_mode="Markdown")
    return ConversationHandler.END


async def show_channels(q, context):
    conn = get_db()
    chs = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    if not chs:
        await q.message.reply_text(
            "📢 *Force Join Channels*\n\nKoi channel add nahi hai. Abhi add karo!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        styled(
                            "➕ Add Channel",
                            style="success",
                            icon=EMOJI_SUCCESS,
                            callback_data="admin_addch",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )
        return
    text = "📢 *Force Join Channels*\n\n"
    kb = [
        [
            styled(
                "➕ Add Channel",
                style="success",
                icon=EMOJI_SUCCESS,
                callback_data="admin_addch",
            )
        ]
    ]
    for ch in chs:
        uname = f"@{ch['username']}" if ch["username"] else str(ch["chat_id"])
        text += f"🔸 {ch['title']} ({uname})\n"
        kb.append(
            [
                styled(
                    f"🗑️ Remove - {ch['title']}",
                    style="danger",
                    icon=EMOJI_DANGER,
                    callback_data=f"admin_delch_{ch['id']}",
                )
            ]
        )
    await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def admin_btn(update, context):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass
    if not is_admin(q.from_user.id):
        return ConversationHandler.END
    data = q.data

    if data == "admin_addlink":
        await q.message.reply_text(
            "➕ *Spotify Links Bhejo*\n\n"
            "Ek message me ek ya multiple links bhejo (space ya new line se alag kar sakte ho).\n\n"
            "Example:\n`https://www.spotify.com/in-en/ppt/hm2m/?code=rN23RRehTJ`\n\n"
            "⚠️ Duplicate links automatically skip ho jayenge!",
            reply_markup=InlineKeyboardMarkup([[home_btn()]]),
            parse_mode="Markdown",
        )
        return ADD_LINK

    if data == "admin_dellink":
        await q.message.reply_text(
            "➖ *Remove karne wala link bhejo*\n\nJo link delete karna hai woh copy karke bhejo.",
            reply_markup=InlineKeyboardMarkup([[home_btn()]]),
        )
        return DEL_LINK

    if data == "admin_addch":
        await q.message.reply_text(
            "📢 *Channel ka link / username / ID bhejo*\n\n"
            "Example: `https://t.me/mychannel` ya `@mychannel` ya channel ID\n\n"
            "⚠️ Bot ko channel me *Admin* banana zaroori hai!",
            reply_markup=InlineKeyboardMarkup([[home_btn()]]),
            parse_mode="Markdown",
        )
        return ADD_CH

    if data == "admin_delch":
        await q.message.reply_text(
            "🗑️ *Delete karne wale channel ka username ya ID bhejo*",
            reply_markup=InlineKeyboardMarkup([[home_btn()]]),
        )
        return DEL_CH

    if data == "admin_broadcast":
        await q.message.reply_text(
            "📣 *Broadcast message bhejo*\n\nYe message sabhi users ko jayega. ✉️",
            reply_markup=InlineKeyboardMarkup([[home_btn()]]),
        )
        return BROADCAST_MSG

    if data.startswith("admin_delch_"):
        chid = int(data.split("_")[-1])
        conn = get_db()
        conn.execute("DELETE FROM channels WHERE id=?", (chid,))
        conn.commit()
        conn.close()
        await q.message.reply_text("🗑️ Channel force join se hata diya gaya!")
        await show_channels(q, context)
        return ConversationHandler.END

    if data == "admin_links":
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) c FROM links").fetchone()["c"]
        used = conn.execute("SELECT COUNT(*) c FROM links WHERE used_by != 0").fetchone()["c"]
        conn.close()
        remaining = total - used
        await q.message.reply_text(
            f"📊 *Links Status*\n\n"
            f"🔗 Total Links: `{total}`\n"
            f"✅ Used: `{used}`\n"
            f"🟢 Remaining: `{remaining}`"
        )
        return ConversationHandler.END

    if data == "admin_users":
        conn = get_db()
        total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        total_refs = conn.execute("SELECT SUM(total_refs) s FROM users").fetchone()["s"] or 0
        total_claims = conn.execute("SELECT SUM(claimed) s FROM users").fetchone()["s"] or 0
        conn.close()
        await q.message.reply_text(
            f"👥 *Users Stats*\n\n"
            f"👤 Total Users: `{total_users}`\n"
            f"🔗 Total Referrals: `{total_refs}`\n"
            f"🎁 Total Claims: `{total_claims}`"
        )
        return ConversationHandler.END

    if data == "admin_channels":
        await show_channels(q, context)
        return ConversationHandler.END

    if data == "admin_home":
        await show_admin_home(q, context)
        return ConversationHandler.END

    if data == "admin_admins":
        await show_admins(q, context)
        return ConversationHandler.END

    if data == "admin_addadmin":
        await q.message.reply_text(
            "👤 *Admin banane wale user ka ID ya @username bhejo*\n\n"
            "Example: `123456789` ya `@username`\n\n"
            "❌ Cancel: /cancel",
            parse_mode="Markdown",
        )
        return ADD_ADMIN

    if data.startswith("admin_deladmin_"):
        aid = int(data.split("_")[-1])
        if aid in ADMIN_IDS:
            await q.message.reply_text("❌ Ye main admin hai — remove nahi kar sakte!")
            await show_admins(q, context)
            return ConversationHandler.END
        conn = get_db()
        conn.execute("DELETE FROM admins WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        await q.message.reply_text("🗑️ Admin remove ho gaya!")
        await show_admins(q, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def show_admin_home(q, context):
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    total_links = conn.execute("SELECT COUNT(*) c FROM links").fetchone()["c"]
    used_links = conn.execute("SELECT COUNT(*) c FROM links WHERE used_by != 0").fetchone()["c"]
    conn.close()
    text = (
        "🛠️ *Admin Panel* 🛠️\n"
        f"{SEP}\n"
        f"👤 Users: `{total_users}`  •  🟢 Links Left: `{total_links - used_links}`\n"
        f"{SEP}"
    )
    await q.message.reply_text(text, reply_markup=admin_kb(), parse_mode="Markdown")


def home_btn():
    return styled("🏠 Home", style="primary", icon=EMOJI_PRIMARY2, callback_data="admin_home")


async def show_admins(q, context):
    conn = get_db()
    db_admins = conn.execute("SELECT * FROM admins").fetchall()
    conn.close()
    text = "👤 *Admins List*\n\n"
    kb = [
        [
            styled(
                "➕ Add Admin",
                style="success",
                icon=EMOJI_SUCCESS,
                callback_data="admin_addadmin",
            ),
            home_btn(),
        ]
    ]
    for a in db_admins:
        text += f"🔸 Admin ID: `{a['id']}`\n"
        kb.append(
            [
                styled(
                    f"🗑️ Remove - {a['id']}",
                    style="danger",
                    icon=EMOJI_DANGER,
                    callback_data=f"admin_deladmin_{a['id']}",
                )
            ]
        )
    text += f"\n🔹 Main Admins: `{', '.join(str(i) for i in ADMIN_IDS)}`\n\n"
    await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# --------------------- ADMIN INPUTS ---------------------

async def add_links(update, context):
    text = update.message.text
    urls = [u.strip() for u in re.split(r"[\s,;]+", text) if u.startswith("http")]
    conn = get_db()
    added, dup = 0, 0
    for u in urls:
        try:
            conn.execute("INSERT INTO links (url) VALUES (?)", (u,))
            added += 1
        except sqlite3.IntegrityError:
            dup += 1
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"✅ *{added}* link add ho gaye! 🎉\n"
        f"⚠️ *{dup}* duplicate links skip kiye (pehle se maujood the)."
    )
    return ConversationHandler.END


async def del_link(update, context):
    url = update.message.text.strip()
    conn = get_db()
    cur = conn.execute("DELETE FROM links WHERE url = ?", (url,))
    conn.commit()
    removed = cur.rowcount
    conn.close()
    if removed:
        await update.message.reply_text("✅ Link remove ho gaya!")
    else:
        await update.message.reply_text("❌ Ye link mila nahi!")
    return ConversationHandler.END


async def add_ch(update, context):
    txt = update.message.text.strip()
    username = None
    chat_id = None
    if txt.startswith("@"):
        username = txt[1:]
    elif "t.me/" in txt:
        username = txt.split("t.me/")[-1].strip("/")
    elif txt.lstrip("-").isdigit():
        chat_id = int(txt)
    else:
        await update.message.reply_text("❌ Invalid input! Channel link (@channel) ya ID bhejo.")
        return ConversationHandler.END
    try:
        if username:
            chat = await context.bot.get_chat(f"@{username}")
        else:
            chat = await context.bot.get_chat(chat_id)
        chat_id = chat.id
        title = chat.title or "Channel"
        username = chat.username
    except Exception:
        await update.message.reply_text(
            "❌ Channel nahi mila! Check karo:\n"
            "1️⃣ Bot ko channel me admin banao\n"
            "2️⃣ Sahi username / link bhejo"
        )
        return ConversationHandler.END
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM channels WHERE chat_id=?", (chat_id,)).fetchone()
    if exists:
        conn.close()
        await update.message.reply_text("⚠️ Ye channel pehle se add hai!")
        return ConversationHandler.END
    conn.execute(
        "INSERT INTO channels (chat_id, title, username) VALUES (?,?,?)",
        (chat_id, title, username),
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"✅ *{title}* force join me add ho gaya!\n"
        f"Ab se users ko claim se pehle ise join karna hoga. 🔒"
    )
    return ConversationHandler.END


async def del_ch(update, context):
    txt = update.message.text.strip()
    username = txt[1:] if txt.startswith("@") else txt
    conn = get_db()
    if username.lstrip("-").isdigit():
        cur = conn.execute("DELETE FROM channels WHERE chat_id=?", (int(username),))
    else:
        cur = conn.execute("DELETE FROM channels WHERE username=?", (username,))
    conn.commit()
    removed = cur.rowcount
    conn.close()
    if removed:
        await update.message.reply_text("✅ Channel remove ho gaya!")
    else:
        await update.message.reply_text("❌ Ye channel mila nahi!")
    return ConversationHandler.END


async def broadcast(update, context):
    msg = update.message.text
    conn = get_db()
    users = conn.execute("SELECT id FROM users").fetchall()
    conn.close()
    ok = fail = 0
    for u in users:
        try:
            await context.bot.send_message(u["id"], f"📣\n\n{msg}")
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(
        f"📣 *Broadcast Report*\n"
        f"{SEP}\n"
        f"✅ Sent: `{ok}`\n"
        f"❌ Failed: `{fail}`",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def add_admin(update, context):
    txt = update.message.text.strip()
    user_id = None
    if txt.startswith("@"):
        try:
            chat = await context.bot.get_chat(txt)
            user_id = chat.id
        except Exception:
            await update.message.reply_text("❌ Ye user nahi mila! Sahi @username bhejo.")
            return ConversationHandler.END
    elif txt.lstrip("-").isdigit():
        user_id = int(txt)
    else:
        await update.message.reply_text("❌ Invalid input! User ID ya @username bhejo.")
        return ConversationHandler.END
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM admins WHERE id=?", (user_id,)).fetchone()
    if exists or user_id in ADMIN_IDS:
        conn.close()
        await update.message.reply_text("⚠️ Ye user pehle se admin hai!")
        return ConversationHandler.END
    conn.execute("INSERT INTO admins (id, added_at) VALUES (?,?)", (user_id, now()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ `{user_id}` ko admin bana diya gaya! 🎉")
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("❌ Cancelled!")
    return ConversationHandler.END


# --------------------- MAIN ---------------------

def main():
    init_db()
    # Python 3.14 fix: PTB ko ek event loop set karke dena zaroori hai
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_btn, pattern="^admin_")],
        states={
            ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_links)],
            DEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_link)],
            ADD_CH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ch)],
            DEL_CH: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_ch)],
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin)],
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler(["admin", "panel"], admin_cmd),
            CallbackQueryHandler(admin_btn, pattern="^admin_"),
            CallbackQueryHandler(check_join_cb, pattern="^check_join$"),
            CallbackQueryHandler(claim_cb, pattern="^claim_reward$"),
            CallbackQueryHandler(stats_cb, pattern="^show_stats$"),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler(["admin", "panel"], admin_cmd))
    app.add_handler(CallbackQueryHandler(check_join_cb, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(claim_cb, pattern="^claim_reward$"))
    app.add_handler(CallbackQueryHandler(stats_cb, pattern="^show_stats$"))
    app.add_handler(conv)
    app.add_error_handler(error_handler)

    logger.info("SpotifyXRefer Bot started... 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()