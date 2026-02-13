import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import instaloader

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Instaloader
L = instaloader.Instaloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 I'm ready! Send me an Instagram link or username.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # 1. Check if it's a Username (for Profile Pic) - looks for text without spaces or links
    if "instagram.com" not in text and " " not in text and not text.startswith("/"):
        username = text.replace("@", "")
        await update.message.reply_text(f"🔍 Searching for profile: {username}...")
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            await update.message.reply_photo(profile.profile_pic_url, caption=f"📸 Profile Pic: {username}")
        except Exception as e:
            await update.message.reply_text("❌ User not found or private.")
        return

    # 2. Check if it's a Link (for Reels/Posts)
    if "instagram.com" in text:
        await update.message.reply_text("⏳ Downloading... (Wait 5-10s)")
        try:
            # Get shortcode (works for reel/p/tv links)
            shortcode = text.split("/")[4]
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            if post.is_video:
                await update.message.reply_video(post.video_url, caption="✅ Downloaded!")
            else:
                await update.message.reply_photo(post.url, caption="✅ Downloaded!")
        except Exception as e:
            await update.message.reply_text("❌ Failed. Link might be private or broken.")
    else:
        await update.message.reply_text("❌ Send a valid Instagram link or username.")

if __name__ == '__main__':
    # GET TOKEN
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("CRITICAL ERROR: You forgot to add the BOT_TOKEN in Zeabur variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        print("Bot is alive!")
        app.run_polling()
