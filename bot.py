import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import phonenumbers
from phonenumbers import carrier, geocoder, timezone

# Get token from environment
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Phone Number Lookup Bot**\n\n"
        "Send /num with phone number\n"
        "Example: `/num +14155552671`",
        parse_mode='Markdown'
    )

async def num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ Please provide a number!\nExample: /num +14155552671")
            return
        
        phone = context.args[0]
        
        # Parse number
        parsed = phonenumbers.parse(phone, None)
        
        if not phonenumbers.is_valid_number(parsed):
            await update.message.reply_text("❌ Invalid phone number!")
            return
        
        # Get details
        country = geocoder.description_for_number(parsed, 'en')
        carrier_name = carrier.name_for_number(parsed, 'en') or "Unknown"
        timezones = ', '.join(timezone.time_zones_for_number(parsed))
        
        # Determine number type
        num_type = get_number_type(phonenumbers.number_type(parsed))
        
        # Format message
        details = f"📱 **Phone Number Details**\n\n"
        details += f"🔢 **Number:** `{phone}`\n"
        details += f"🌍 **Country:** {country}\n"
        details += f"📡 **Carrier:** {carrier_name}\n"
        details += f"🏷️ **Type:** {num_type}\n"
        details += f"⏰ **Timezone:** {timezones}\n"
        details += f"✅ **Valid:** ✓ Yes\n"
        details += f"\n📞 **Formats:**\n"
        details += f"• `{phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}`\n"
        details += f"• `{phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)}`"
        
        await update.message.reply_text(details, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def get_number_type(num_type):
    types = {
        0: "Fixed Line", 1: "Mobile", 2: "Fixed Line/Mobile",
        3: "Toll Free", 4: "Premium Rate", 5: "Shared Cost",
        6: "VoIP", 7: "Personal Number", 8: "Pager",
        9: "Universal Access", 10: "Unknown"
    }
    return types.get(num_type, "Unknown")

def main():
    """Start the bot"""
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num_command))
    
    # Start bot (using webhook for Zeabur)
    port = int(os.environ.get('PORT', 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://your-app-name.zeabur.app"  # Change this later
    )

if __name__ == '__main__':
    main()        
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("num", get_number_info))
        
        print("✅ Phone Bot Started...")
        app_bot.run_polling()
