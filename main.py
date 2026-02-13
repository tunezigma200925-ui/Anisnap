import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

# --- 1. KEEP ALIVE (Server) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Phone Bot is Alive!"

def run_flask():
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

# --- 3. BOT COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🕵️‍♂️ **PHONE INFO BOT**\n"
        "━━━━━━━━━━━━━━━━\n"
        "I can scan any mobile number to find:\n"
        "📍 Location (State/Country)\n"
        "📡 Sim Operator (Jio/Airtel/etc)\n"
        "🕒 Timezone\n\n"
        "**How to use:**\n"
        "Type `/num` followed by the number with country code.\n\n"
        "Example:\n"
        "`/num +919876543210`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def get_number_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user sent a number
    if not context.args:
        await update.message.reply_text("❌ **Usage:** `/num +919999999999`\n(Don't forget the country code!)", parse_mode="Markdown")
        return

    phone_input = context.args[0]
    
    msg = await update.message.reply_text(f"🔍 **Scanning** `{phone_input}`...", parse_mode="Markdown")

    try:
        # Parse the number
        parsed_number = phonenumbers.parse(phone_input, None)
        
        # Check validity
        if not phonenumbers.is_valid_number(parsed_number):
            await msg.edit_text("❌ **Invalid Number.** Please check the digits and country code.")
            return

        # 1. Get Location (Region/Country)
        region = geocoder.description_for_number(parsed_number, "en")
        
        # 2. Get Carrier (ISP/Sim Company)
        sim_company = carrier.name_for_number(parsed_number, "en")
        
        # 3. Get Timezone
        time_zones = timezone.time_zones_for_number(parsed_number)
        
        # 4. Format Number
        formatted_num = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

        # Create the Report
        response = (
            f"🕵️‍♂️ **SCAN RESULT**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📞 **Number:** `{formatted_num}`\n"
            f"📍 **Location:** {region}\n"
            f"📡 **Operator:** {sim_company}\n"
            f"🕒 **Timezone:** {', '.join(time_zones)}\n"
            f"✅ **Valid:** Yes"
        )
        
        await msg.edit_text(response, parse_mode="Markdown")

    except phonenumbers.NumberParseException:
        await msg.edit_text("❌ **Error:** Format not recognized. Try adding `+91` (or your country code) at the start.", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ **Error:** {str(e)}")

if __name__ == '__main__':
    # Get Token
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Error: BOT_TOKEN is missing in Zeabur!")
    else:
        keep_alive()
        
        app_bot = ApplicationBuilder().token(TOKEN).build()
        
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("num", get_number_info))
        
        print("✅ Phone Bot Started...")
        app_bot.run_polling()
