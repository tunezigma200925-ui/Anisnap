import os
import logging
import time
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import instaloader

# --- 1. KEEP ALIVE SERVER (Fixes Zeabur stopping the bot) ---
app = Flask('')
@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. SETUP LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 3. INSTALOADER SETUP ---
L = instaloader.Instaloader()
L.compress_json = False 
L.context.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Try Login (Safe Mode: Won't crash if login fails)
INSTA_USER = os.getenv("INSTA_USER")
INSTA_PASS = os.getenv("INSTA_PASS")
LOGGED_IN = False

if INSTA_USER and INSTA_PASS:
    try:
        L.load_session_from_file(INSTA_USER) # Try load session
    except FileNotFoundError:
        try:
            L.login(INSTA_USER, INSTA_PASS)
            LOGGED_IN = True
            print(f"✅ Login Successful as {INSTA_USER}")
        except Exception as e:
            print(f"⚠️ Login Failed: {e}")
            print("Bot will work in 'Public Mode' (No stories/Private posts).")

# --- 4. BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **INSTAGRAM DOWNLOADER BOT** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 **Hello!** I can download:\n"
        "🎥 Reels & Videos\n"
        "📸 Profile Pictures (HD)\n"
        "📊 Account Statistics\n"
        "📹 Stories (Login Required)\n\n"
        "👇 **Just send me a Link or Username!**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # CASE A: IT IS A LINK
    if "instagram.com" in text:
        msg = await update.message.reply_text("⏳ **Processing Link...**", parse_mode="Markdown")
        try:
            # Extract Shortcode
            if "/reel/" in text or "/p/" in text:
                shortcode = text.split("/")[4]
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                
                caption_text = (
                    f"✨ **Downloaded via Bot**\n"
                    f"👤 **By:** {post.owner_username}\n"
                    f"❤️ **Likes:** {post.likes:,}\n"
                    f"📅 **Date:** {post.date_local.strftime('%Y-%m-%d')}"
                )

                if post.is_video:
                    await update.message.reply_video(post.video_url, caption=caption_text, parse_mode="Markdown")
                else:
                    await update.message.reply_photo(post.url, caption=caption_text, parse_mode="Markdown")
                
                await msg.delete() # Remove "Processing" message
            else:
                await msg.edit_text("❌ **Error:** Please send a valid Reel or Post link.", parse_mode="Markdown")

        except Exception as e:
            await msg.edit_text(f"❌ **Failed:** {str(e)}\n\n_Make sure the account is public._", parse_mode="Markdown")

    # CASE B: IT IS A USERNAME
    else:
        username = text.replace("@", "").replace("/", "")
        msg = await update.message.reply_text(f"🔍 **Searching for @{username}...**", parse_mode="Markdown")
        
        try:
            # Create Buttons
            keyboard = [
                [InlineKeyboardButton("📸 Get DP (HD)", callback_data=f"dp_{username}")],
                [InlineKeyboardButton("📊 Get 15+ Details", callback_data=f"info_{username}")],
                [InlineKeyboardButton("📹 Get Stories", callback_data=f"story_{username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await msg.edit_text(
                f"👤 **User Found:** `@{username}`\n"
                f"👇 What would you like to do?",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            await msg.edit_text("❌ **User not found.** Check the spelling.", parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Stop loading animation
    
    data = query.data
    action, username = data.split("_")
    
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        
        if action == "dp":
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=profile.profile_pic_url,
                caption=f"📸 **HD Profile Pic:** `@{username}`",
                parse_mode="Markdown"
            )

        elif action == "info":
            info_text = (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 **ACCOUNT STATS: @{username}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **ID:** `{profile.userid}`\n"
                f"📛 **Name:** {profile.full_name}\n"
                f"🔵 **Verified:** {'✅ Yes' if profile.is_verified else '❌ No'}\n"
                f"🔒 **Private:** {'🔒 Yes' if profile.is_private else '🔓 No'}\n"
                f"🏢 **Business:** {'✅ Yes' if profile.is_business_account else '❌ No'}\n"
                f"👥 **Followers:** {profile.followers:,}\n"
                f"👣 **Following:** {profile.followees:,}\n"
                f"📸 **Total Posts:** {profile.mediacount:,}\n"
                f"📺 **IGTV Count:** {profile.igtvcount}\n"
                f"🔗 **Link:** {profile.external_url if profile.external_url else 'None'}\n"
                f"📝 **Bio:**\n_{profile.biography}_"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=info_text, parse_mode="Markdown")

        elif action == "story":
            if not LOGGED_IN:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ **Login Required:** The owner needs to set INSTA_USER and INSTA_PASS in Zeabur variables to download stories.")
                return

            msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⏳ **Fetching Stories for @{username}...**", parse_mode="Markdown")
            
            stories = L.get_stories(userids=[profile.userid])
            count = 0
            for story in stories:
                for item in story.get_items():
                    try:
                        if item.is_video:
                            await context.bot.send_video(chat_id=update.effective_chat.id, video=item.video_url)
                        else:
                            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item.url)
                        count += 1
                    except:
                        continue
            
            await msg.delete()
            if count == 0:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ **No active stories found.**")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ **All stories sent!**")

    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ **Error:** {str(e)}")

# --- 5. RUN BOT ---
if __name__ == '__main__':
    # Start Keep Alive for Zeabur
    keep_alive()
    
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ Error: BOT_TOKEN is missing!")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.add_handler(CallbackQueryHandler(button_click))
        
        print("✅ Bot is Running...")
        app_bot.run_polling()            for story in stories:
                for item in story.get_items():
                    if item.is_video:
                        await context.bot.send_video(chat_id=update.effective_chat.id, video=item.video_url)
                    else:
                        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item.url)
                    count += 1
            
            if count == 0:
                 await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ No active stories found.")
            else:
                 await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ All stories sent!")

        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Failed to get stories: {e}")

if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("Error: BOT_TOKEN missing")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("Bot is Running...")
        app.run_polling()
