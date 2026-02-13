import os
import logging
import time
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import instaloader

# --- 1. KEEP ALIVE SERVER (CRITICAL FOR ZEABUR) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Zeabur requires binding to 0.0.0.0 and the correct PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. SETUP LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. INSTALOADER SETUP ---
L = instaloader.Instaloader()
L.compress_json = False 
# Fake a browser user agent to avoid detection
L.context.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# --- 4. SAFE LOGIN (PREVENTS CRASHES) ---
INSTA_USER = os.getenv("INSTA_USER")
INSTA_PASS = os.getenv("INSTA_PASS")
LOGGED_IN = False

if INSTA_USER and INSTA_PASS:
    print(f"🔐 Attempting login for {INSTA_USER}...")
    try:
        # Try to login, but catch errors if Instagram blocks it
        L.login(INSTA_USER, INSTA_PASS)
        LOGGED_IN = True
        print("✅ Login Successful!")
    except Exception as e:
        print(f"⚠️ LOGIN FAILED: {e}")
        print("➡️ Bot continuing in PUBLIC MODE (Reels & DPs only).")
        # We do NOT exit. We let the bot run without login.

# --- 5. BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **INSTAGRAM DOWNLOADER BOT** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 **Hello!** I am online.\n\n"
        "Send me a **Link** (Reel/Post) or a **Username**.\n\n"
        f"🔐 **Login Status:** {'✅ Connected' if LOGGED_IN else '⚠️ Public Mode (No Stories)'}"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # CASE A: LINK
    if "instagram.com" in text:
        status_msg = await update.message.reply_text("⏳ **Processing...**")
        try:
            # Clean URL
            if "/reel/" in text or "/p/" in text:
                shortcode = text.split("/")[4].split("?")[0] # Fix for URLs with ?igshid
                
                # Get Post
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                
                caption = f"✨ **Downloaded**\n👤 {post.owner_username}\n📅 {post.date_local.strftime('%Y-%m-%d')}"

                if post.is_video:
                    await update.message.reply_video(post.video_url, caption=caption, parse_mode="Markdown")
                else:
                    await update.message.reply_photo(post.url, caption=caption, parse_mode="Markdown")
                
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Send a valid Reel or Post link.")

        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}\n\n_Make sure the account is Public._")

    # CASE B: USERNAME
    else:
        username = text.replace("@", "").replace("/", "").strip()
        msg = await update.message.reply_text(f"🔍 **Looking up @{username}...**")
        
        try:
            # We don't need login for basic profile pic
            profile = instaloader.Profile.from_username(L.context, username)
            
            keyboard = [
                [InlineKeyboardButton("📸 Get DP (HD)", callback_data=f"dp_{username}")],
                [InlineKeyboardButton("📊 Get Info", callback_data=f"info_{username}")],
                [InlineKeyboardButton("📹 Get Stories", callback_data=f"story_{username}")]
            ]
            
            await msg.edit_text(
                f"👤 **Found:** `@{username}`", 
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await msg.edit_text("❌ **User not found.**")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, username = data.split("_")
    
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        
        if action == "dp":
            await context.bot.send_photo(update.effective_chat.id, profile.profile_pic_url, caption=f"📸 `@{username}`", parse_mode="Markdown")

        elif action == "info":
            info = (
                f"📊 **STATS: @{username}**\n"
                f"━━━━━━━━━━\n"
                f"👥 Followers: {profile.followers}\n"
                f"👣 Following: {profile.followees}\n"
                f"📸 Posts: {profile.mediacount}\n"
                f"📝 Bio: {profile.biography}"
            )
            await context.bot.send_message(update.effective_chat.id, info, parse_mode="Markdown")

        elif action == "story":
            if not LOGGED_IN:
                await context.bot.send_message(update.effective_chat.id, "❌ **Login Failed/Missing.** Cannot download stories.")
                return
            
            await context.bot.send_message(update.effective_chat.id, "⏳ Fetching stories...")
            stories = L.get_stories(userids=[profile.userid])
            count = 0
            for story in stories:
                for item in story.get_items():
                    if item.is_video:
                        await context.bot.send_video(update.effective_chat.id, item.video_url)
                    else:
                        await context.bot.send_photo(update.effective_chat.id, item.url)
                    count += 1
            if count == 0:
                 await context.bot.send_message(update.effective_chat.id, "❌ No active stories.")

    except Exception as e:
        await context.bot.send_message(update.effective_chat.id, f"❌ Error: {e}")

if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ CRITICAL ERROR: BOT_TOKEN is missing in Zeabur Variables.")
    else:
        # Start Web Server in background
        keep_alive()
        
        # Start Bot
        app_bot = ApplicationBuilder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.add_handler(CallbackQueryHandler(button_click))
        
        print("✅ Bot is running...")
        app_bot.run_polling()
