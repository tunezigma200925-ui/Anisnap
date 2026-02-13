import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import requests

# Get token from environment variable (set in Zeabur dashboard)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """
🔍 **Phone Number Lookup Bot** 🔍

Welcome! I can show you details about any phone number.

**Commands:**
/num +1234567890 - Lookup a number
/examples - Try example numbers
/countries - Supported countries
/help - Show help

**Example:** `/num +14155552671`

🌍 Works with 200+ countries!
    """
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇺🇸 USA", callback_data='+14155552671'),
         InlineKeyboardButton("🇬🇧 UK", callback_data='+442079460000')],
        [InlineKeyboardButton("🇮🇳 India", callback_data='+919999999999'),
         InlineKeyboardButton("🇨🇳 China", callback_data='+8613912345678')],
        [InlineKeyboardButton("🇯🇵 Japan", callback_data='+81312345678'),
         InlineKeyboardButton("🇧🇷 Brazil", callback_data='+5511912345678')],
        [InlineKeyboardButton("🇩🇪 Germany", callback_data='+49301234567'),
         InlineKeyboardButton("🇫🇷 France", callback_data='+33123456789')],
        [InlineKeyboardButton("🇷🇺 Russia", callback_data='+79161234567'),
         InlineKeyboardButton("🇿🇦 South Africa", callback_data='+27123456789')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📱 **Choose an example number:**", 
                                   reply_markup=reply_markup, 
                                   parse_mode='Markdown')

async def countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🌍 **Supported Countries**

This bot works with phone numbers from ALL countries!

**Popular country codes:**
🇺🇸 USA: +1
🇬🇧 UK: +44
🇮🇳 India: +91
🇨🇳 China: +86
🇯🇵 Japan: +81
🇩🇪 Germany: +49
🇫🇷 France: +33
🇧🇷 Brazil: +55
🇷🇺 Russia: +7
🇦🇺 Australia: +61

Just send any number with country code!
    """
    await update.message.reply_text(msg, parse_mode='Markdown')

async def num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a number!\n"
                "Example: `/num +14155552671`",
                parse_mode='Markdown'
            )
            return
        
        phone = context.args[0]
        
        # Parse number
        parsed = phonenumbers.parse(phone, None)
        
        # Check if valid
        if not phonenumbers.is_valid_number(parsed):
            await update.message.reply_text(
                "❌ **Invalid phone number!**\n"
                "Make sure to include country code\n"
                "Example: +1 for USA",
                parse_mode='Markdown'
            )
            return
        
        # Get all details
        country = geocoder.description_for_number(parsed, 'en')
        carrier_name = carrier.name_for_number(parsed, 'en')
        if not carrier_name:
            carrier_name = "Unknown/Not available"
        
        timezones = timezone.time_zones_for_number(parsed)
        tz_str = ', '.join(timezones) if timezones else "Unknown"
        
        # Get number type
        num_type = get_number_type(parsed)
        
        # Get region/city if available
        region = geocoder.description_for_number(parsed, 'en')
        
        # Format numbers
        intl_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        
        # Create detailed message
        details = f"📱 **Phone Number Analysis**\n\n"
        details += f"🔢 **Number:** `{phone}`\n"
        details += f"🌍 **Country:** {country}\n"
        details += f"📍 **Region:** {region}\n"
        details += f"📡 **Carrier:** {carrier_name}\n"
        details += f"🏷️ **Type:** {num_type}\n"
        details += f"⏰ **Timezone:** {tz_str}\n"
        details += f"✅ **Valid:** ✓ Yes\n"
        details += f"📊 **Status:** Active Number\n\n"
        details += "**Number Formats:**\n"
        details += f"📞 **International:** `{intl_format}`\n"
        details += f"📞 **National:** `{national}`\n"
        details += f"📞 **E.164:** `{e164}`\n\n"
        details += "**Additional Info:**\n"
        details += f"🌐 **Country Code:** +{parsed.country_code}\n"
        details += f"📱 **National Number:** {parsed.national_number}\n"
        
        if carrier_name != "Unknown/Not available":
            details += f"\n📡 **Network:** {carrier_name}"
        
        await update.message.reply_text(details, parse_mode='Markdown')
        
    except phonenumbers.NumberParseException:
        await update.message.reply_text(
            "❌ **Invalid format!**\n"
            "Use: /num +[country code][number]\n"
            "Example: `/num +14155552671`",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def get_number_type(parsed_number):
    num_type = phonenumbers.number_type(parsed_number)
    types = {
        0: "📞 Fixed Line",
        1: "📱 Mobile",
        2: "📞 Fixed Line or Mobile",
        3: "🎯 Toll Free",
        4: "💎 Premium Rate",
        5: "🔄 Shared Cost",
        6: "💻 VoIP",
        7: "👤 Personal Number",
        8: "📟 Pager",
        9: "🌐 Universal Access",
        10: "❓ Unknown"
    }
    return types.get(num_type, "❓ Unknown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    number = query.data
    context.args = [number]
    await num_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
**📖 How to Use This Bot**

1️⃣ **Lookup a number:**
   `/num +1234567890`

2️⃣ **Include country code:**
   • USA: +1
   • UK: +44
   • India: +91
   • China: +86

3️⃣ **What you'll get:**
   • 🌍 Country & Region
   • 📡 Carrier/Network
   • 🏷️ Number Type (Mobile/Landline)
   • ⏰ Timezone
   • ✅ Validation Status
   • 📞 Multiple Formats

4️⃣ **Try examples:**
   Click /examples button

**Note:** Owner name and exact address are private and not available for free.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logging.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ ERROR: No BOT_TOKEN found!")
        print("Please set BOT_TOKEN in Zeabur environment variables")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(CommandHandler("countries", countries))
    app.add_handler(CommandHandler("num", num_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    print("🤖 Phone Number Bot is starting on Zeabur...")
    print(f"✅ Bot token configured: {BOT_TOKEN[:5]}...")
    
    # Start polling (works on Zeabur)
    app.run_polling()

if __name__ == '__main__':
    main()
