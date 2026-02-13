import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import instaloader

# 1. Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Initialize Instaloader
L = instaloader.Instaloader()

# 3. Try to Login (Required for Stories)
INSTA_USER = os.getenv("INSTA_USER")
INSTA_PASS = os.getenv("INSTA_PASS")
LOGGED_IN = False

if INSTA_USER and INSTA_PASS:
    try:
        L.login(INSTA_USER, INSTA_PASS)
        LOGGED_IN = True
        print(f"✅ Logged in as {INSTA_USER}")
    except Exception as e:
        print(f"❌ Login Failed: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me an Instagram Link (Reel/Post) OR a Username!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # CASE A: It is a LINK (Reel/Post)
    if "instagram.com" in text:
        await update.message.reply_text("⏳ Downloading Media... Please wait.")
        try:
            shortcode = text.split("/")[4] if "reel" in text or "p/" in text else None
            if not shortcode: raise Exception("Invalid Link")
            
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            if post.is_video:
                await update.message.reply_video(post.video_url, caption="✅ Here is your Reel")
            else:
                await update.message.reply_photo(post.url, caption="✅ Here is your Photo")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to download link. Error: {e}")

    # CASE B: It is a USERNAME (Profile)
    else:
        username = text.replace("@", "").strip()
        await update.message.reply_text(f"🔍 Analyzing profile: {username}...")
        
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            
            # 1. Collect 15+ Details
            details = (
                f"👤 **User:** {profile.username}\n"
                f"🆔 **ID:** `{profile.userid}`\n"
                f"📛 **Name:** {profile.full_name}\n"
                f"🔵 **Verified:** {'Yes' if profile.is_verified else 'No'}\n"
                f"🔒 **Private:** {'Yes' if profile.is_private else 'No'}\n"
                f"🏢 **Business:** {'Yes' if profile.is_business_account else 'No'}\n"
                f"👥 **Followers:** {profile.followers}\n"
                f"👣 **Following:** {profile.followees}\n"
                f"📸 **Total Posts:** {profile.mediacount}\n"
                f"📺 **IGTV Count:** {profile.igtvcount}\n"
                f"🔗 **External URL:** {profile.external_url if profile.external_url else 'None'}\n"
                f"📝 **Bio:** \n{profile.biography}\n"
            )

            # 2. Add Button for Stories
            keyboard = [[InlineKeyboardButton("📥 Download Stories", callback_data=f"story_{username}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # 3. Send Profile Pic (HD) and Details
            await update.message.reply_photo(
                photo=profile.profile_pic_url,
                caption=details,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text("❌ User not found or unexpected error.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Close loading circle
    
    data = query.data
    if data.startswith("story_"):
        username = data.replace("story_", "")
        
        if not LOGGED_IN:
            await query.edit_message_caption(caption="❌ **Error:** I cannot download stories because I am not logged in.\n\nOwner: Please add INSTA_USER and INSTA_PASS to Zeabur variables.", parse_mode="Markdown")
            return

        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⏳ Fetching stories for {username}...")
        
        try:
            # Get User ID to fetch stories
            profile = instaloader.Profile.from_username(L.context, username)
            stories = L.get_stories(userids=[profile.userid])
            
            count = 0
            for story in stories:
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
