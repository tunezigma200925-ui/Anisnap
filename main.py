import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import instaloader

# 1. Setup Logging (Helps you see errors on Zeabur website)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

L = instaloader.Instaloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I am running on Zeabur! Send me a link.")

async def downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" in url:
        await update.message.reply_text("Processing... Please wait.")
        try:
            # Basic logic for shortcode
            if "reel" in url or "p/" in url:
                shortcode = url.split("/")[4] 
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                
                if post.is_video:
                    await update.message.reply_video(post.video_url)
                else:
                    await update.message.reply_photo(post.url)
            else:
                 await update.message.reply_text("Please send a Reel/Post link.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
    else:
        await update.message.reply_text("Not an Instagram link.")

if __name__ == '__main__':
    # 2. Get Token from "Environment Variable" (Safer for clouds)
    # If you are lazy, you can replace os.getenv('BOT_TOKEN') with "YOUR_TOKEN_HERE"
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        print("Error: BOT_TOKEN is missing!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), downloader))
        
        print("Bot is starting...")
        app.run_polling()
