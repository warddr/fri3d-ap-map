#!/usr/bin/env python
# pylint: disable=unused-argument

import logging
import configparser


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import sqlite3

con = sqlite3.connect("telegrambot.db")
cur = con.cursor()

config = configparser.ConfigParser()
config.read('config.ini')


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

AP_NUMBER, PHOTO, LOCATION, SWITCHPORT = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome, you can use /cancel at any time to stop without saving\nGive the AP number:",
        reply_markup=ReplyKeyboardRemove(),
    )

    return AP_NUMBER


async def ap_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("AP number of %s: %s", user.first_name, update.message.text)

    if update.message.text.isnumeric():
        await update.message.reply_text(
            "I see! Please send me a photo of the AP, if you don't want to add a photo send /skip ",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["ap_number"] = update.message.text
        return PHOTO
    else:
        await update.message.reply_text(
            "Only numbers here please, try again! ",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AP_NUMBER



async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive("static/ap-pictures/" + context.user_data["ap_number"] + ".jpg")
    logger.info("Photo of %s: %s", user.first_name, context.user_data["ap_number"] + ".jpg")


    kb = [[KeyboardButton('send location', request_location=True)],
          [KeyboardButton('/skip')]]
    kb_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)



    await update.message.reply_text(
        "Gorgeous! Now, send me your location please, or send /skip if you don't want to.", reply_markup=kb_markup,
    )

    return LOCATION

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the photo and asks for a location."""
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)



    kb = [[KeyboardButton('send location', request_location=True)],
          [KeyboardButton('/skip')]]
    kb_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)



    await update.message.reply_text(
        ":( Now, send me your location please, or send /skip.", reply_markup=kb_markup,
    )

    return LOCATION


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_location = update.message.location
    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )
    context.user_data["lat"] = user_location.latitude
    context.user_data["lon"] = user_location.longitude
    await update.message.reply_text(
        "Maybe I can visit it sometime! At last, send me the port on the switch:", reply_markup=ReplyKeyboardRemove(),
    )

    return SWITCHPORT


async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user
    logger.info("User %s did not send a location.", user.first_name)
    await update.message.reply_text(
        "You seem a bit paranoid! At last, send me the port on the switch:"
    )

    return SWITCHPORT


async def switchport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text("Thank you! Use /start again to add more AP's.")
    context.user_data["port"] = update.message.text
    data = [
    (context.user_data["ap_number"], context.user_data["lat"], context.user_data["lon"], context.user_data["port"]),
    ]
    cur.executemany("INSERT INTO AP(number, lat, lon, switchport) VALUES(?, ?, ?, ?)", data)
    con.commit()

    logger.info("finished: AP %s at location %s, %s in switch port %s", context.user_data["ap_number"], context.user_data["lat"], context.user_data["lon"], context.user_data["port"] )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config['DEFAULT']['TelegramToken']).build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_number)],
            PHOTO: [MessageHandler(filters.PHOTO, photo), CommandHandler("skip", skip_photo)],
            LOCATION: [
                MessageHandler(filters.LOCATION, location),
                CommandHandler("skip", skip_location),
            ],
            SWITCHPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, switchport)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
