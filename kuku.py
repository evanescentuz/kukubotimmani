from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import requests
import re

# Constants
BOT_TOKEN = '6668891430:AAGJ1-l-xPkNdQGXU94-ij_BzEqSUUxX1CU'
IMGBB_API_KEY = '9b4ea7191130c0e88a6b43c3f45dde6c'

# States
CONFIRMATION, MANUAL_CHARACTER_NAME, MANUAL_ANIME_NAME, MANUAL_RARITY, MANUAL_EVENT = range(5)

# Mappings
RARITY_MAP = {
    '⚪': 1, '🟣': 2, '🟢': 3, '🟡': 4, '🔮': 5, '💮': 6, '🎐': 7
}
EVENT_MAP = {
    '🏖': 1, '👘': 2, '❄️': 3, '💞': 4, '🎒': 5, '🎃': 6, '🎮': 7, '🪼': 8,
    '🏀': 9, '🧹': 10, '☔️': 11, '🐰': 12, '🌸': 13, '🎸': 14, '🎄': 15, '🤓': 16,
    '💍': 17, '🎊': 18, '🎨': 19, '🏨': 20
}

# Function to upload file to ImgBB
def upload_to_imgbb(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={'key': IMGBB_API_KEY},
                files={'image': f}
            )
        response_data = response.json()
        if response_data['success']:
            return response_data['data']['url']
        return None
    except Exception as e:
        print(f"Error uploading to ImgBB: {str(e)}")
        return None

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Send a photo with a caption!")
    return CONFIRMATION

# Extract information from the caption
def extract_info(caption):
    print(f"Caption received: {caption}")  # Debugging line
    try:
        # Extract anime name
        anime_match = re.search(r'OwO! Check out This Anime!\n\n(.+)', caption)
        # Extract character name
        character_match = re.search(r'(\d+)\s+(.+?)\n', caption)
        # Extract rarity
        rarity_match = re.search(r'(\S) 𝙍𝘼𝙍𝙄𝙏𝙔', caption)
        
        print(f"Anime match: {anime_match}, Character match: {character_match}, Rarity match: {rarity_match}")  # Debugging
        
        if not (anime_match and character_match and rarity_match):
            return None  # If any of these three are missing, return None

        anime_name = anime_match.group(1).strip()
        character_name = character_match.group(2).strip()
        rarity_symbol = rarity_match.group(1).strip()

        # Map rarity symbol to number
        rarity = RARITY_MAP.get(rarity_symbol, None)
        
        # Try to extract event, default to 21 if not found
        event_match = re.search(r'\[(\S+)\]', caption)
        event = EVENT_MAP.get(event_match.group(1), 21) if event_match else 21
        
        print(f"Event match: {event_match}, Event value: {event}")  # Debugging

        return {
            'anime_name': anime_name,
            'character_name': character_name,
            'rarity': rarity,
            'event': event
        }
    except Exception as e:
        print(f"Error extracting information: {str(e)}")
        return None



# Handle photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_path = await file.download_as_bytearray()

        # Save the downloaded file temporarily
        with open("temp_image.jpg", "wb") as f:
            f.write(file_path)

        context.user_data['image_path'] = "temp_image.jpg"

        # Extract information from caption
        caption = update.message.caption
        extracted_info = extract_info(caption)

        if extracted_info:
            context.user_data.update(extracted_info)

            # Ask for confirmation
            keyboard = [
                [InlineKeyboardButton("Yes", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"Is this information correct?\n\n"
                f"Character: {extracted_info['character_name']}\n"
                f"Anime: {extracted_info['anime_name']}\n"
                f"Rarity: {extracted_info['rarity']}\n"
                f"Event: {extracted_info['event']}",
                reply_markup=reply_markup
            )
            return CONFIRMATION
        else:
            await update.message.reply_text("Couldn't extract the information. Please provide details manually.")
            return MANUAL_CHARACTER_NAME
    else:
        await update.message.reply_text("Please send a photo.")
        return CONFIRMATION

# Handle confirmation callback
async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "yes":
        # Upload image and send order details
        imgbb_url = upload_to_imgbb(context.user_data['image_path'])
        character_name = context.user_data['character_name'].replace(" ", "-").title()
        anime_name = context.user_data['anime_name'].replace(" ", "-").title()
        rarity = context.user_data['rarity']
        event = context.user_data['event']

        await query.edit_message_text(
            f"/upload {imgbb_url} {character_name} {anime_name} {rarity} {event}"
        )
        return ConversationHandler.END
    else:
        # Ask for manual input
        await query.edit_message_text("Please provide the character's name.")
        return MANUAL_CHARACTER_NAME

# Handle manual input for character name
async def handle_manual_character_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['character_name'] = update.message.text.strip().replace(" ", "-").title()
    await update.message.reply_text("Please provide the anime's name.")
    return MANUAL_ANIME_NAME

# Handle manual input for anime name
async def handle_manual_anime_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['anime_name'] = update.message.text.strip().replace(" ", "-").title()
    await update.message.reply_text(
        "Choose rarity:\n1 (⚪️ Common)\n2 (🟣 Rare)\n3 (🟢 Medium)\n4 (🟡 Legendary)\n5 (🔮 Limited)\n6 (💮 Special)\n7 (🎐 Celestial)"
    )
    return MANUAL_RARITY

# Handle manual input for rarity
async def handle_manual_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rarity = update.message.text.strip()
    if rarity.isdigit() and 1 <= int(rarity) <= 7:
        context.user_data['rarity'] = rarity
        await update.message.reply_text(
            "Choose event:\n1: 𝑺𝒖𝒎𝒎𝒆𝒓 🏖\n2: 𝑲𝒊𝒎𝒐𝒏𝒐 👘\n3: 𝑾𝒊𝒏𝒕𝒆𝒓 ❄️\n4: 𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆 💞\n5: 𝑺𝒄𝒉𝒐𝒐𝒍 🎒\n6: 𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏 🎃\n"
            "7: 𝑮𝒂𝒎𝒆 🎮\n8: 𝑴𝒂𝒓𝒊𝒏𝒆 🪼\n9: 𝑩𝒂𝒔𝒌𝒆𝒕𝒃𝒂𝒍𝒍 🏀\n10: 𝑴𝒂𝒊𝒅 🧹\n11: 𝑹𝒂𝒊𝒏 ☔\n12: 𝑩𝒖𝒏𝒏𝒚 🐰\n"
            "13: 𝑭𝒍𝒐𝒘𝒆𝒓 🌸\n14: 𝑴𝒖𝒔𝒊𝒄 🎸\n15: 𝑪𝒉𝒓𝒊𝒔𝒕𝒎𝒂𝒔 🎄\n16: 𝑵𝒆𝒓𝒅 🤓\n17: 𝑾𝒆𝒅𝒅𝒊𝒏𝒈 💍\n18: 𝑵𝒆𝒘 𝒀𝒆𝒂𝒓 🎊\n19: 𝑷𝒂𝒊𝒏𝒕 🎨\n20: 𝑯𝒐𝒕𝒆𝒍 🏨\n 21: None"
        )
        return MANUAL_EVENT
    else:
        await update.message.reply_text("Invalid rarity. Please enter a number between 1 and 7.")
        return MANUAL_RARITY

# Handle manual input for event
async def handle_manual_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event = update.message.text.strip()
    if event.isdigit() and 1 <= int(event) <= 21:
        context.user_data['event'] = event

        # Upload the image
        imgbb_url = upload_to_imgbb(context.user_data['image_path'])
        character_name = context.user_data['character_name']
        anime_name = context.user_data['anime_name']
        rarity = context.user_data['rarity']
        event = context.user_data['event']

        await update.message.reply_text(
            f"/upload {imgbb_url} {character_name} {anime_name} {rarity} {event}"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid event. Please enter a number between 1 and 21.")
        return MANUAL_EVENT

# Main function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
        MANUAL_CHARACTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_character_name)],
        MANUAL_ANIME_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_anime_name)],
        MANUAL_RARITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_rarity)],
        MANUAL_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_event)],
    },
    fallbacks=[]
)

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()

if __name__ == "__main__":
    main()
